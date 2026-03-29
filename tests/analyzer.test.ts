import { describe, it, expect } from 'vitest';
import { analyzeIngredients, parseIngredientList } from '../lib/analyzer';

// ── analyzeIngredients ─────────────────────────────────────────────────────────

describe('analyzeIngredients', () => {
  it('returns Permissible for clean ingredients', () => {
    const result = analyzeIngredients('Sugar, Water, Salt, Flour');
    expect(result.status).toBe('Permissible');
    expect(result.ingredients).toHaveLength(0); // no flagged codes
  });

  it('returns Avoid when explicit haram keyword present', () => {
    const result = analyzeIngredients('Sugar, Lard, Salt');
    expect(result.status).toBe('Avoid');
    expect(result.ingredients.some((i) => i.status === 'Avoid')).toBe(true);
  });

  it('returns Avoid for pork variants', () => {
    expect(analyzeIngredients('Contains PORK').status).toBe('Avoid');
    expect(analyzeIngredients('Contains BABI').status).toBe('Avoid');
    expect(analyzeIngredients('Contains PORC').status).toBe('Avoid');
  });

  it('returns Avoid for alcohol keywords', () => {
    expect(analyzeIngredients('Wine flavour').status).toBe('Avoid');
    expect(analyzeIngredients('Alkohol 96%').status).toBe('Avoid');
  });

  it('returns Doubtful for gelatin', () => {
    const result = analyzeIngredients('Gelatin, Sugar');
    expect(result.status).toBe('Doubtful');
  });

  it('returns Doubtful for emulsifier keyword', () => {
    const result = analyzeIngredients('Water, Emulsifier');
    expect(result.status).toBe('Doubtful');
  });

  it('detects E-numbers in E471 format', () => {
    const result = analyzeIngredients('Water, E471, Sugar');
    expect(result.ingredients.some((i) => i.code === 'E471')).toBe(true);
  });

  it('detects E-numbers with space: "E 471"', () => {
    const result = analyzeIngredients('Water, E 471, Sugar');
    expect(result.ingredients.some((i) => i.code === 'E471')).toBe(true);
  });

  it('detects bare numeric codes matching E-number DB', () => {
    const result = analyzeIngredients('Contains 471');
    expect(result.ingredients.some((i) => i.code === 'E471')).toBe(true);
  });

  it('returns Permissible for empty string', () => {
    const result = analyzeIngredients('');
    expect(result.status).toBe('Permissible');
    expect(result.ingredients).toHaveLength(0);
  });

  it('Avoid overrides Doubtful', () => {
    const result = analyzeIngredients('Gelatin, Lard');
    expect(result.status).toBe('Avoid');
  });

  it('is case-insensitive', () => {
    expect(analyzeIngredients('lard').status).toBe('Avoid');
    expect(analyzeIngredients('GELATIN').status).toBe('Doubtful');
    expect(analyzeIngredients('e471').status).not.toBe('Unknown');
  });
});

// ── parseIngredientList ────────────────────────────────────────────────────────

describe('parseIngredientList', () => {
  it('splits comma-separated ingredients', () => {
    const result = parseIngredientList('Sugar, Water, Salt');
    expect(result.length).toBeGreaterThanOrEqual(3);
    expect(result.map((r) => r.raw)).toContain('Sugar');
  });

  it('returns empty array for empty string', () => {
    expect(parseIngredientList('')).toEqual([]);
  });

  it('marks lard as Avoid', () => {
    const result = parseIngredientList('Sugar, Lard, Water');
    const lard = result.find((r) => r.raw.toLowerCase() === 'lard');
    expect(lard?.status).toBe('Avoid');
  });

  it('marks gelatin as flagged (Avoid or Doubtful — not Permissible)', () => {
    // Gelatin is in the DB as Avoid (animal source uncertain) — not permissible
    const result = parseIngredientList('Gelatin, Sugar');
    const gel = result.find((r) => r.raw.toLowerCase().includes('gelatin'));
    expect(gel?.status).not.toBe('Permissible');
    expect(gel?.status).not.toBe('Unknown');
  });

  it('recognises E-numbers embedded in tokens', () => {
    const result = parseIngredientList('Water, Emulsifier (E471), Sugar');
    const entry = result.find((r) => r.raw.includes('E471') || r.raw.includes('471'));
    expect(entry).toBeDefined();
  });

  it('deduplicates identical ingredients', () => {
    const result = parseIngredientList('Sugar, Water, Sugar');
    const sugars = result.filter((r) => r.raw.toLowerCase() === 'sugar');
    expect(sugars).toHaveLength(1);
  });

  it('filters out very short tokens', () => {
    const result = parseIngredientList('Sugar, a, Water');
    expect(result.every((r) => r.raw.length > 2)).toBe(true);
  });

  it('extracts from "Ingredients:" section header', () => {
    const label = `Net weight: 200g\nIngredients: Sugar, Water, Salt\nAllergens: none`;
    const result = parseIngredientList(label);
    expect(result.some((r) => r.raw === 'Sugar')).toBe(true);
  });

  it('assigns Unknown to unrecognised ingredients', () => {
    const result = parseIngredientList('Xylitol, Quinine');
    // At least one should be Unknown (not in DB)
    expect(result.some((r) => r.status === 'Unknown')).toBe(true);
  });
});
