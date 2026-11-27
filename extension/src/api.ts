import type { MetaResponse, SearchRequest, SearchResponse } from "./types";

const DEFAULT_BACKEND = "http://localhost:8000";

export async function getBackendUrl(): Promise<string> {
  const stored = await chrome.storage.local.get("backendUrl");
  const url = (stored.backendUrl as string | undefined) || DEFAULT_BACKEND;
  return url.replace(/\/+$/, "");
}

export async function saveBackendUrl(url: string): Promise<void> {
  await chrome.storage.local.set({ backendUrl: url.replace(/\/+$/, "") });
}

export async function fetchMeta(): Promise<MetaResponse> {
  const res = await fetch(`${await getBackendUrl()}/api/meta`);
  if (!res.ok) throw new Error(`Backend injoignable (HTTP ${res.status}).`);
  return res.json() as Promise<MetaResponse>;
}

export async function fetchDefaultCountry(): Promise<string> {
  try {
    const res = await fetch(`${await getBackendUrl()}/api/geo/defaults`);
    if (!res.ok) return "FR";
    const body = (await res.json()) as { destination_country: string };
    return body.destination_country || "FR";
  } catch {
    return "FR";
  }
}

export async function runSearch(request: SearchRequest, signal: AbortSignal): Promise<SearchResponse> {
  const res = await fetch(`${await getBackendUrl()}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const message = (body as { message?: string }).message || `Erreur backend (HTTP ${res.status}).`;
    throw new Error(message);
  }
  return body as SearchResponse;
}
