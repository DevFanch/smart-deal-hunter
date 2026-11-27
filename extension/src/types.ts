export interface SearchFilters {
  brand?: string | null;
  model?: string | null;
  sku?: string | null;
  color?: string | null;
  size?: string | null;
  condition?: string | null;
  price_min?: number | null;
  price_max?: number | null;
  country?: string | null;
  make?: string | null;
  car_model?: string | null;
  year?: number | null;
  part_type?: string | null;
  part_brand?: string | null;
  oem_reference?: string | null;
}

export interface SearchRequest {
  query: string;
  category?: string | null;
  filters: SearchFilters;
  wholesale: boolean;
  deep_search: boolean;
  quantity?: number | null;
  destination_country: string;
  postal_code?: string | null;
  currency: string;
}

export interface Offer {
  url: string;
  shop: string;
  title: string;
  brand?: string | null;
  sku?: string | null;
  image_url?: string | null;
  price?: number | null;
  currency?: string | null;
  shipping_cost?: number | null;
  shipping_status: string;
  total_cost?: number | null;
  condition?: string | null;
  availability?: string | null;
  seller_country?: string | null;
  match_level: string;
  match_reason: string;
  checked_at: string;
  moq?: number | null;
  supplier_type?: string | null;
  platform?: string | null;
  commercial_terms?: string | null;
}

export interface Lead {
  url: string;
  site: string;
  detected_name: string;
  detected_price?: number | null;
  detected_currency?: string | null;
  reason_not_verified: string;
  platform?: string | null;
  moq_detected?: number | null;
  potentially_stale: boolean;
}

export interface SearchResponse {
  query: string;
  currency: string;
  destination_country: string;
  fx: { base: string; rates: Record<string, number>; source: string; fetched_at: string };
  verified_offers: Offer[];
  leads: Lead[];
  diagnostics: {
    total_ms: number;
    sources_queried: number;
    results_detected: number;
    offers_verified: number;
    leads: number;
    errors: string[];
    warnings: string[];
  };
  deep_search_notice?: string | null;
  commercial_warnings: string[];
}

export interface MetaResponse {
  categories: string[];
  countries: string[];
  currencies: string[];
  quantities: number[];
  max_query_length: number;
  deep_search_available: boolean;
  monthly_budget_eur: number;
}
