import { fetchDefaultCountry, fetchMeta, runSearch } from "./api";
import { QueryRejected, sanitizeQuery, setSafeText } from "./sanitize";
import type { MetaResponse, SearchFilters, SearchResponse } from "./types";

const $ = <T extends HTMLElement>(id: string): T => document.getElementById(id) as T;

const state = {
  meta: null as MetaResponse | null,
  country: "FR",
  currency: "EUR",
};

/* ---------- Filtres dynamiques par catégorie ---------- */

const SHOE_SIZES_EU = ["36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48"];
const SHOE_SIZES_US_M = ["6", "6.5", "7", "7.5", "8", "8.5", "9", "9.5", "10", "10.5", "11", "12", "13"];
const SHOE_SIZES_US_W = ["4", "5", "6", "7", "8", "9", "10", "11", "12"];
const SHOE_SIZES_UK = ["3", "4", "5", "6", "7", "8", "9", "10", "11", "12"];
const CLOTHING_SIZES = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "XXXL"];
const CLOTHING_TYPES = ["T-shirt", "Sweat", "Pull", "Veste", "Jacket", "Chemise", "Manteau"];
const COLORS = ["Noir", "Blanc", "Bleu", "Rouge", "Vert", "Gris", "Beige", "Marron", "Jaune", "Rose", "Orange", "Violet"];
const CONDITIONS: [string, string][] = [["", "Indifférent"], ["new", "Neuf"], ["used", "Occasion"]];

interface FieldDef {
  key: keyof SearchFilters;
  label: string;
  type: "text" | "number" | "select";
  options?: (string | [string, string])[];
  placeholder?: string;
}

const FILTERS: Record<string, FieldDef[]> = {
  Chaussures: [
    { key: "brand", label: "Marque", type: "text", placeholder: "Nike, Adidas…" },
    { key: "model", label: "Modèle", type: "text", placeholder: "Air Max 90…" },
    { key: "size", label: "Pointure (EU)", type: "select", options: ["", ...SHOE_SIZES_EU] },
    { key: "color", label: "Couleur", type: "select", options: ["", ...COLORS] },
    { key: "condition", label: "État", type: "select", options: CONDITIONS },
  ],
  Vêtements: [
    { key: "brand", label: "Marque", type: "text" },
    { key: "model", label: "Type (T-shirt, Veste…)", type: "select", options: ["", ...CLOTHING_TYPES] },
    { key: "size", label: "Taille", type: "select", options: ["", ...CLOTHING_SIZES] },
    { key: "color", label: "Couleur", type: "select", options: ["", ...COLORS] },
    { key: "condition", label: "État", type: "select", options: CONDITIONS },
  ],
  Automobile: [
    { key: "make", label: "Constructeur", type: "text", placeholder: "Bosch, Renault…" },
    { key: "car_model", label: "Modèle véhicule", type: "text" },
    { key: "year", label: "Année", type: "number", placeholder: "2015" },
    { key: "oem_reference", label: "Référence OEM/OE", type: "text", placeholder: "0125812015" },
    { key: "part_brand", label: "Marque de la pièce", type: "text" },
    { key: "condition", label: "État", type: "select", options: CONDITIONS },
  ],
  Autres: [
    { key: "brand", label: "Marque", type: "text" },
    { key: "model", label: "Modèle", type: "text" },
    { key: "sku", label: "Référence fabricant", type: "text" },
    { key: "price_min", label: "Prix min", type: "number" },
    { key: "price_max", label: "Prix max", type: "number" },
    { key: "condition", label: "État", type: "select", options: CONDITIONS },
  ],
};

function renderFilters(category: string): void {
  const container = $("filters");
  container.textContent = "";
  const defs = FILTERS[category] ?? FILTERS["Autres"];
  for (const def of defs) {
    const label = document.createElement("label");
    label.className = "lbl";
    setSafeText(label, def.label);
    container.appendChild(label);

    let input: HTMLInputElement | HTMLSelectElement;
    if (def.type === "select") {
      input = document.createElement("select");
      for (const opt of def.options ?? []) {
        const [value, text] = Array.isArray(opt) ? opt : [opt, opt];
        const option = document.createElement("option");
        option.value = value;
        setSafeText(option, text);
        input.appendChild(option);
      }
    } else {
      input = document.createElement("input");
      input.type = def.type;
      if (def.placeholder) input.placeholder = def.placeholder;
    }
    input.id = `f-${def.key}`;
    container.appendChild(input);
  }
}

function collectFilters(): SearchFilters {
  const filters: SearchFilters = {};
  for (const defs of Object.values(FILTERS)) {
    for (const def of defs) {
      const el = document.getElementById(`f-${def.key}`) as HTMLInputElement | HTMLSelectElement | null;
      if (!el || !el.value.trim()) continue;
      const key = def.key;
      (filters as Record<string, unknown>)[key] =
        def.type === "number" ? Number(el.value) : el.value.trim();
    }
  }
  return filters;
}

/* ---------- Options globales ---------- */

function fillSelect(el: HTMLSelectElement, values: (string | number)[], selected?: string): void {
  el.textContent = "";
  for (const value of values) {
    const option = document.createElement("option");
    option.value = String(value);
    setSafeText(option, value === "" ? "— Indifférent —" : value);
    el.appendChild(option);
  }
  if (selected) el.value = selected;
}

/* ---------- Rendu des résultats ---------- */

function badge(text: string, cssClass: string): HTMLElement {
  const span = document.createElement("span");
  span.className = `badge ${cssClass}`;
  setSafeText(span, text);
  return span;
}

const MATCH_LABELS: Record<string, string> = {
  exacte: "Correspondance exacte",
  tres_probable: "Très probable",
  approximative: "Approximative",
  non_confirmee: "Non confirmée",
};
const SHIP_LABELS: Record<string, string> = {
  confirme: "Livraison confirmée",
  estime: "Livraison estimée",
  inconnu: "Livraison inconnue",
};

function renderOffer(offer: SearchResponse["verified_offers"][number]): HTMLElement {
  const card = document.createElement("div");
  card.className = "card";

  const title = document.createElement("div");
  title.className = "title";
  setSafeText(title, offer.title || "(sans nom)");
  card.appendChild(title);

  const priceLine = document.createElement("div");
  if (offer.price !== null && offer.price !== undefined) {
    const price = document.createElement("span");
    price.className = "price";
    setSafeText(price, `${offer.price.toFixed(2)} ${offer.currency ?? ""}`);
    priceLine.appendChild(price);
  }
  if (offer.total_cost !== null && offer.total_cost !== undefined) {
    const total = document.createElement("span");
    total.className = "total";
    setSafeText(total, ` · total livré ≈ ${offer.total_cost.toFixed(2)} ${state.currency}`);
    priceLine.appendChild(total);
  }
  card.appendChild(priceLine);

  const badges = document.createElement("div");
  badges.appendChild(badge(MATCH_LABELS[offer.match_level] ?? offer.match_level, offer.match_level));
  badges.appendChild(badge(SHIP_LABELS[offer.shipping_status] ?? offer.shipping_status, `ship-${offer.shipping_status}`));
  card.appendChild(badges);

  const meta: string[] = [
    offer.shop,
    offer.brand ?? undefined,
    offer.sku ? `réf. ${offer.sku}` : undefined,
    offer.seller_country ? `vendeur ${offer.seller_country}` : undefined,
    offer.availability ?? undefined,
    offer.condition === "used" ? "occasion" : offer.condition === "new" ? "neuf" : undefined,
    offer.moq ? `MOQ ${offer.moq}` : undefined,
    offer.supplier_type ? `type : ${offer.supplier_type}` : undefined,
    `vérifié le ${new Date(offer.checked_at).toLocaleString("fr-FR")}`,
  ].filter((v): v is string => Boolean(v));
  const metaEl = document.createElement("div");
  metaEl.className = "meta";
  setSafeText(metaEl, meta.join(" · "));
  card.appendChild(metaEl);

  if (offer.commercial_terms) {
    const warn = document.createElement("div");
    warn.className = "warn";
    setSafeText(warn, offer.commercial_terms);
    card.appendChild(warn);
  }

  const link = document.createElement("a");
  link.href = offer.url;
  link.target = "_blank";
  link.rel = "noopener noreferrer nofollow";
  setSafeText(link, "Voir chez le marchand ↗");
  card.appendChild(link);
  return card;
}

function renderLead(lead: SearchResponse["leads"][number]): HTMLElement {
  const card = document.createElement("div");
  card.className = "card";
  const title = document.createElement("div");
  title.className = "title";
  setSafeText(title, lead.detected_name);
  card.appendChild(title);
  const meta = document.createElement("div");
  meta.className = "meta";
  const price = lead.detected_price !== null && lead.detected_price !== undefined
    ? ` · prix détecté ${lead.detected_price} ${lead.detected_currency ?? ""} (potentiellement obsolète)` : "";
  setSafeText(meta, `${lead.site}${lead.platform ? ` (${lead.platform})` : ""}${price} · motif : ${lead.reason_not_verified}`);
  card.appendChild(meta);
  const link = document.createElement("a");
  link.href = lead.url;
  link.target = "_blank";
  link.rel = "noopener noreferrer nofollow";
  setSafeText(link, "Vérifier ce site ↗");
  card.appendChild(link);
  return card;
}

function renderResults(response: SearchResponse): void {
  $("screen-results").classList.remove("hidden");
  $("progress").classList.add("hidden");

  const warnings = $("warnings");
  warnings.textContent = "";
  for (const w of response.commercial_warnings) {
    const el = document.createElement("div");
    el.className = "warn";
    setSafeText(el, w);
    warnings.appendChild(el);
  }
  if (response.deep_search_notice) {
    const el = document.createElement("div");
    el.className = "hint";
    setSafeText(el, response.deep_search_notice);
    warnings.appendChild(el);
  }

  const offers = $("offers");
  offers.textContent = "";
  setSafeText($("count-verified"), `(${response.verified_offers.length})`);
  if (response.verified_offers.length === 0) {
    const el = document.createElement("p");
    el.className = "hint";
    setSafeText(el, "Aucune offre vérifiée pour le moment : consultez les pistes ci-dessous.");
    offers.appendChild(el);
  }
  for (const offer of response.verified_offers) offers.appendChild(renderOffer(offer));

  const leads = $("leads");
  leads.textContent = "";
  setSafeText($("count-leads"), `(${response.leads.length})`);
  if (response.leads.length === 0) {
    const el = document.createElement("p");
    el.className = "hint";
    setSafeText(el, "Aucune piste supplémentaire détectée.");
    leads.appendChild(el);
  }
  for (const lead of response.leads) leads.appendChild(renderLead(lead));

  const d = response.diagnostics;
  setSafeText(
    $("diagnostics"),
    `${d.sources_queried} source(s) interrogée(s) · ${d.results_detected} résultat(s) détecté(s) · ` +
    `${d.offers_verified} offre(s) vérifiée(s) · ${d.leads} piste(s) · ${d.total_ms} ms` +
    (d.errors.length ? ` · erreurs : ${d.errors.join(" ; ")}` : ""),
  );
}

function showError(message: string): void {
  const el = $("query-error");
  el.classList.remove("hidden");
  setSafeText(el, message);
}

/* ---------- Initialisation ---------- */

async function init(): Promise<void> {
  const query = $<HTMLInputElement>("query");
  const category = $<HTMLSelectElement>("category");
  const country = $<HTMLSelectElement>("country");
  const currency = $<HTMLSelectElement>("currency");
  const quantity = $<HTMLSelectElement>("quantity");

  category.addEventListener("change", () => renderFilters(category.value));
  $<HTMLInputElement>("wholesale").addEventListener("change", (e) => {
    quantity.disabled = !(e.target as HTMLInputElement).checked;
  });

  const stored = await chrome.storage.local.get(["currency", "backendUrl"]);
  state.currency = (stored.currency as string) || "EUR";

  try {
    state.meta = await fetchMeta();
    fillSelect(category, ["", ...state.meta.categories], "");
    fillSelect(country, state.meta.countries, await fetchDefaultCountry());
    fillSelect(currency, state.meta.currencies, state.currency);
    fillSelect(quantity, state.meta.quantities, "12");
    if (stored.backendUrl) $<HTMLInputElement>("backend-url").value = stored.backendUrl;
  } catch {
    fillSelect(country, ["FR", "DE", "ES", "IT", "GB", "US", "CN"], "FR");
    fillSelect(currency, ["EUR", "USD", "GBP"], "EUR");
    fillSelect(quantity, [1, 2, 5, 10, 12, 20, 24, 50, 100, 200, 500, 1000], "12");
    showError("Backend injoignable. Démarrez le backend puis renseignez son URL dans les préférences (⚙).");
  }

  $<HTMLInputElement>("deep").addEventListener("change", (e) => {
    const notice = $("deep-notice");
    notice.classList.toggle("hidden", !(e.target as HTMLInputElement).checked);
  });

  $<HTMLButtonElement>("btn-prefs").addEventListener("click", () => {
    $("screen-search").classList.add("hidden");
    $("screen-results").classList.add("hidden");
    $("screen-prefs").classList.remove("hidden");
  });
  $<HTMLButtonElement>("btn-prefs-back").addEventListener("click", () => {
    $("screen-prefs").classList.add("hidden");
    $("screen-search").classList.remove("hidden");
  });
  $<HTMLButtonElement>("btn-back").addEventListener("click", () => {
    $("screen-results").classList.add("hidden");
    $("screen-search").classList.remove("hidden");
  });

  $<HTMLButtonElement>("btn-search").addEventListener("click", async () => {
    clearError();
    let cleanQuery: string;
    try {
      cleanQuery = sanitizeQuery(query.value);
    } catch (err) {
      showError(err instanceof QueryRejected ? err.message : "Requête invalide.");
      return;
    }
    query.value = cleanQuery;

    $("screen-search").classList.add("hidden");
    $("screen-results").classList.remove("hidden");
    $("progress").classList.remove("hidden");
    const btn = $<HTMLButtonElement>("btn-search");
    btn.disabled = true;

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 90_000);
    try {
      const response = await runSearch({
        query: cleanQuery,
        category: category.value || null,
        filters: collectFilters(),
        wholesale: $<HTMLInputElement>("wholesale").checked,
        deep_search: $<HTMLInputElement>("deep").checked,
        quantity: Number(quantity.value) || null,
        destination_country: country.value,
        currency: currency.value,
      }, controller.signal);
      renderResults(response);
      await chrome.storage.local.set({ currency: currency.value });
    } catch (err) {
      $("progress").classList.add("hidden");
      const el = document.createElement("p");
      el.className = "error";
      setSafeText(el, err instanceof Error ? err.message : "Erreur inattendue.");
      $("screen-results").prepend(el);
    } finally {
      clearTimeout(timeout);
      btn.disabled = false;
    }
  });
}

function clearError(): void {
  const el = $("query-error");
  el.classList.add("hidden");
  setSafeText(el, "");
}

document.addEventListener("DOMContentLoaded", () => { void init(); });
