import { NextRequest, NextResponse } from 'next/server';

export const maxDuration = 30;

const PROMPT = `You are an OCR system specialized in reading food product ingredient labels.

Your task:
1. Find the ingredient list on this food label (look for "Ingredients", "Bahan-bahan", "Ingrédients", or similar headers in any language).
2. Extract every ingredient exactly as printed, preserving all original text including E-numbers (e.g. E471, E120).
3. Return ONLY the raw ingredient text as a single comma-separated list — no headers, no commentary, no markdown.
4. If the label has multiple languages, include all of them.
5. If you cannot find a clear ingredient list, return whatever text is readable on the label.`;

export async function POST(request: NextRequest) {
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
      console.error('Gemini error:', err);
      return NextResponse.json({ error: err }, { status: geminiRes.status });
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
