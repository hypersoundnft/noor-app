import { NextRequest, NextResponse } from 'next/server';
import { Ratelimit } from '@upstash/ratelimit';
import { Redis } from '@upstash/redis';

export const maxDuration = 30;

// Rate limiter: 10 scans per IP per hour — only active when Upstash is configured
const ratelimit =
  process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN
    ? new Ratelimit({
        redis: Redis.fromEnv(),
        limiter: Ratelimit.slidingWindow(10, '1 h'),
        analytics: false,
        prefix: 'noor:ocr',
      })
    : null;

const PROMPT = `You are an OCR system specialized in reading food product ingredient labels.

Your task:
1. Find the ingredient list on this food label (look for "Ingredients", "Bahan-bahan", "Ingrédients", or similar headers in any language).
2. Extract every ingredient exactly as printed, preserving all original text including E-numbers (e.g. E471, E120).
3. Return ONLY the raw ingredient text as a single comma-separated list — no headers, no commentary, no markdown.
4. If the label has multiple languages, include all of them.
5. If you cannot find a clear ingredient list, return whatever text is readable on the label.`;

// Allow requests only from the Noor site itself (blocks cross-origin abuse)
function isAllowedOrigin(request: NextRequest): boolean {
  const origin = request.headers.get('origin') ?? '';
  const referer = request.headers.get('referer') ?? '';
  if (!origin && !referer) return true; // server-side / no-cors same-origin
  const allowed = [
    'https://noor-app-official.vercel.app',
    // VERCEL_PROJECT_PRODUCTION_URL is the stable project URL (set automatically by Vercel)
    process.env.VERCEL_PROJECT_PRODUCTION_URL
      ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}`
      : '',
    // VERCEL_URL covers preview deployments
    process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : '',
    'http://localhost:3000',
    'http://localhost:3001',
  ].filter(Boolean);
  return allowed.some((o) => origin.startsWith(o) || referer.startsWith(o));
}

export async function POST(request: NextRequest) {
  if (!isAllowedOrigin(request)) {
    return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
  }

  // IP-based rate limiting via Upstash Redis (skipped if not configured)
  if (ratelimit) {
    const ip = request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ?? 'anonymous';
    const { success, limit, remaining } = await ratelimit.limit(ip);
    if (!success) {
      return NextResponse.json(
        { error: 'Too many scans — please wait before trying again.' },
        {
          status: 429,
          headers: {
            'X-RateLimit-Limit': String(limit),
            'X-RateLimit-Remaining': String(remaining),
          },
        },
      );
    }
  }

  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    return NextResponse.json({ error: 'GEMINI_API_KEY is not configured.' }, { status: 500 });
  }

  try {
    const formData = await request.formData();
    const image = formData.get('image') as File | null;
    if (!image) {
      return NextResponse.json({ error: 'No image provided.' }, { status: 400 });
    }

    const bytes = await image.arrayBuffer();
    const base64 = Buffer.from(bytes).toString('base64');
    const mimeType = image.type || 'image/jpeg';

    // Direct REST call to Gemini v1 — no SDK, no versioning surprises
    const url = `https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key=${apiKey}`;

    const geminiRes = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [{
          parts: [
            { inline_data: { mime_type: mimeType, data: base64 } },
            { text: PROMPT },
          ],
        }],
        generationConfig: { temperature: 0 },
      }),
    });

    if (!geminiRes.ok) {
      const err = await geminiRes.text();
      console.error('Gemini error:', geminiRes.status, err);
      // Return a user-friendly message, not raw API internals
      const friendly =
        geminiRes.status === 429 ? 'Too many requests — please wait a moment and try again.' :
        geminiRes.status === 404 ? 'OCR service unavailable. Please try again later.' :
        'OCR service error. Please try again.';
      return NextResponse.json({ error: friendly }, { status: geminiRes.status });
    }

    const data = await geminiRes.json();
    const text: string = data.candidates?.[0]?.content?.parts?.[0]?.text?.trim() ?? '';
    return NextResponse.json({ text });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    console.error('OCR error:', message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
