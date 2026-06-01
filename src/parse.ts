/**
 * Extract the model's final integer answer.
 * Prefers an explicit `ANSWER: <int>` line; falls back to the last integer in the text.
 * Commas and surrounding whitespace are stripped.
 */
export function extractInteger(text: string): number | null {
  const tagged = [...text.matchAll(/ANSWER\s*[:=]\s*\$?\s*(-?[\d,]+)/gi)];
  if (tagged.length > 0) {
    const raw = tagged[tagged.length - 1][1].replace(/,/g, "");
    const n = Number(raw);
    if (Number.isFinite(n)) return n;
  }
  const all = [...text.matchAll(/-?\d[\d,]*/g)].map((m) => m[0].replace(/,/g, ""));
  if (all.length === 0) return null;
  const n = Number(all[all.length - 1]);
  return Number.isFinite(n) ? n : null;
}
