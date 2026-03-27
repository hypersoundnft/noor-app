import eNumbersDB from '@/data/e_numbers.json';
import ingredientsDB from '@/data/ingredients.json';

export type HalalStatus = 'Permissible' | 'Doubtful' | 'Avoid' | 'Unknown';

export type Ingredient = {
  code: string;
  name: string;
  status: HalalStatus;
  description: string;
};

export type DetailedIngredient = {
  raw: string;       // as it appeared on the label
  name: string;      // cleaned display name
  status: HalalStatus;
  reason: string;
};

export type AnalysisResult = {
  ingredients: Ingredient[];
  detailedIngredients: DetailedIngredient[];
  status: HalalStatus;
  rawText: string;
};

const eDb = eNumbersDB as Record<string, { name: string; status: HalalStatus; description: string }>;
const iDb = (ingredientsDB as unknown as Record<string, { status: HalalStatus; reason: string }>);

// ── E-number + keyword scan (existing logic) ──────────────────────────────────

const haramKeywords = ['PORK', 'BABI', 'PORC', 'LARD', 'BACON', 'HAM', 'WINE', 'ALCOHOL', 'ALKOHOL', 'VIN', 'BEER', 'BIERE', 'RUM', 'RHUM', 'LIQUOR', 'CARMINE', 'COCHINEAL'];
const doubtfulKeywords = ['GELATIN', 'GELATINE', 'WHEY', 'RENNET', 'SHORTENING', 'EMULSIFIER', 'EMULSIFIANT', 'MARGARINE'];

export function analyzeIngredients(rawText: string): AnalysisResult {
  if (!rawText) return { ingredients: [], detailedIngredients: [], status: 'Permissible', rawText: '' };

  const normalized = rawText.toUpperCase().replace(/E\s+(\d+)/g, 'E$1');
  const foundSet = new Set<string>();

  let match: RegExpExecArray | null;
  const eNumberRegex = /E-?\s*(\d{3,4}[A-Z]?)/g;
  while ((match = eNumberRegex.exec(normalized)) !== null) foundSet.add(`E${match[1]}`);

  const isolatedRegex = /\b(\d{3,4}[A-Z]?)\b/g;
  while ((match = isolatedRegex.exec(normalized)) !== null) {
    if (eDb[`E${match[1]}`]) foundSet.add(`E${match[1]}`);
  }

  const results: Ingredient[] = [];
  let avoidCount = 0;
  let doubtfulCount = 0;

  haramKeywords.forEach((kw) => {
    if (normalized.includes(kw)) {
      results.push({ code: `TEXT:${kw}`, name: `Explicit Keyword (${kw})`, status: 'Avoid', description: 'Explicit haram or avoidable ingredient detected in the text.' });
      avoidCount++;
    }
  });

  doubtfulKeywords.forEach((kw) => {
    if (normalized.includes(kw) && !results.find((r) => r.code === `TEXT:${kw}`)) {
      results.push({ code: `TEXT:${kw}`, name: `Doubtful Keyword (${kw})`, status: 'Doubtful', description: 'Ingredient source requires further verification.' });
      doubtfulCount++;
    }
  });

  for (const code of foundSet) {
    const entry = eDb[code];
    if (entry) {
      results.push({ code, ...entry });
      if (entry.status === 'Avoid') avoidCount++;
      if (entry.status === 'Doubtful') doubtfulCount++;
    } else {
      results.push({ code, name: 'Unknown Additive', status: 'Doubtful', description: 'Not found in local database. Verify manually.' });
      doubtfulCount++;
    }
  }

  const status: HalalStatus = avoidCount > 0 ? 'Avoid' : doubtfulCount > 0 ? 'Doubtful' : 'Permissible';
  return { ingredients: results, detailedIngredients: parseIngredientList(rawText), status, rawText };
}

// ── Per-ingredient detail parser ──────────────────────────────────────────────

function lookupIngredient(token: string): { status: HalalStatus; reason: string } {
  const upper = token.toUpperCase().trim();

  // 1. Direct match in ingredients DB
  if (iDb[upper]) return iDb[upper];

  // 2. Partial match — check if any DB key is fully contained in the token or vice versa
  for (const key of Object.keys(iDb)) {
    if (upper.includes(key) || key.includes(upper)) return iDb[key];
  }

  // 3. Check E-number DB for codes embedded in the token (e.g. "(E471)")
  const eMatch = upper.match(/E(\d{3,4}[A-Z]?)/);
  if (eMatch) {
    const code = `E${eMatch[1]}`;
    const entry = eDb[code];
    if (entry) return { status: entry.status, reason: `${entry.name}: ${entry.description}` };
  }

  // 4. Haram keyword scan
  for (const kw of haramKeywords) {
    if (upper.includes(kw)) return { status: 'Avoid', reason: `Contains haram keyword "${kw}".` };
  }

  // 5. Doubtful keyword scan
  for (const kw of doubtfulKeywords) {
    if (upper.includes(kw)) return { status: 'Doubtful', reason: `Contains potentially doubtful ingredient "${kw}". Verify source.` };
  }

  return { status: 'Unknown', reason: 'Not found in database. Verify with manufacturer or a scholar.' };
}

export function parseIngredientList(rawText: string): DetailedIngredient[] {
  if (!rawText) return [];

  // Try to isolate the ingredients section (look for "Ingredients:" or "Bahan-bahan:" etc.)
  const sectionRegex = /(?:ingredients?|bahan[- ]?bahan|ingr[eé]dients?|composici[oó]n)\s*[:\-]?\s*([\s\S]+?)(?:\n\n|\n[A-Z]{4,}|$)/i;
  const sectionMatch = rawText.match(sectionRegex);
  const workingText = sectionMatch ? sectionMatch[1] : rawText;

  // Split by comma, semicolon, or bullet. Filter short/noisy tokens.
  const tokens = workingText
    .split(/[,;•\n]/)
    .map((t) => t.replace(/\s+/g, ' ').trim())
    .filter((t) => t.length > 2 && t.length < 80)
    // Remove lines that look like "Contains X% of ..."
    .filter((t) => !/^\d+(\.\d+)?%/.test(t))
    // Remove parenthetical-only tokens like "(emulsifier)"
    .map((t) => t.replace(/^\(|\)$/g, '').trim())
    .filter((t) => t.length > 2);

  // De-duplicate while preserving order
  const seen = new Set<string>();
  const unique = tokens.filter((t) => {
    const key = t.toUpperCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  return unique.map((raw) => {
    const { status, reason } = lookupIngredient(raw);
    return { raw, name: toTitleCase(raw), status, reason };
  });
}

function toTitleCase(str: string): string {
  return str.replace(/\w\S*/g, (w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase());
}
