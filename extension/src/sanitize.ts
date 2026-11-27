/** Sécurisation côté client (miroir des règles backend).
 *  Le texte saisi est une donnée : jamais interprété comme code.
 *  Toute donnée marchande affichée est insérée via textContent (jamais innerHTML). */

export const MAX_QUERY_LENGTH = 160;

const DANGEROUS_SCHEMES = ["javascript:", "data:", "vbscript:", "file:", "about:"];

export class QueryRejected extends Error {}

export function sanitizeQuery(raw: string): string {
  const text = raw.normalize("NFC").replace(/[\u0000-\u001f\u007f-\u009f\u200b-\u200f\u2028\u2029]/g, "");
  const collapsed = text.replace(/\s+/g, " ").trim();
  if (!collapsed) throw new QueryRejected("Requête vide.");
  if (collapsed.length > MAX_QUERY_LENGTH) throw new QueryRejected(`Maximum ${MAX_QUERY_LENGTH} caractères.`);
  const lower = collapsed.toLowerCase();
  if (/[<>]/.test(lower) || DANGEROUS_SCHEMES.some((s) => lower.includes(s))) {
    throw new QueryRejected("La recherche ne peut pas contenir de code ou de balise.");
  }
  return collapsed;
}

export function setSafeText(el: HTMLElement | null, value: unknown): void {
  if (el) el.textContent = value === null || value === undefined ? "" : String(value);
}
