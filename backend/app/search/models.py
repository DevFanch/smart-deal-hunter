"""Modèles de données normalisés du moteur de recherche."""
from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class MatchLevel(str, enum.Enum):
    EXACT = "exacte"
    PROBABLE = "tres_probable"
    APPROXIMATE = "approximative"
    UNCONFIRMED = "non_confirmee"


class ShippingStatus(str, enum.Enum):
    CONFIRMED = "confirme"
    ESTIMATED = "estime"
    UNKNOWN = "inconnu"


class SupplierType(str, enum.Enum):
    MANUFACTURER = "fabricant"
    WHOLESALER = "grossiste"
    DISTRIBUTOR = "distributeur"
    RESELLER = "revendeur"
    INTERMEDIARY = "intermediaire"
    UNKNOWN = "non_determine"


class PriceTier(BaseModel):
    min_qty: int
    unit_price: float | None = None
    currency: str | None = None


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Offer(BaseModel):
    """Offre effectivement vérifiée : la page produit a été consultée à la source."""

    url: str
    shop: str
    title: str = ""
    brand: Optional[str] = None
    model: Optional[str] = None
    sku: Optional[str] = None
    image_url: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    original_currency: Optional[str] = None
    shipping_cost: Optional[float] = None
    shipping_status: ShippingStatus = ShippingStatus.UNKNOWN
    total_cost: Optional[float] = None  # dans la devise cible de comparaison
    condition: Optional[str] = None  # "new" / "used" / None
    availability: Optional[str] = None
    seller_country: Optional[str] = None
    ship_country: Optional[str] = None
    match_level: MatchLevel = MatchLevel.UNCONFIRMED
    match_reason: str = ""
    verified: bool = True
    checked_at: datetime = Field(default_factory=now_utc)
    source_connector: str = "page"
    # Grossistes
    supplier_type: Optional[SupplierType] = None
    platform: Optional[str] = None
    moq: Optional[int] = None
    price_tiers: list[PriceTier] = Field(default_factory=list)
    quantity_applied: Optional[int] = None
    commercial_terms: Optional[str] = None


class Lead(BaseModel):
    """Piste détectée mais non vérifiée (site inaccessible, CAPTCHA, données insuffisantes)."""

    url: str
    site: str
    detected_name: str
    detected_brand: Optional[str] = None
    detected_sku: Optional[str] = None
    detected_price: Optional[float] = None
    detected_currency: Optional[str] = None
    source_connector: str
    detected_at: Optional[datetime] = Field(default_factory=now_utc)
    reason_not_verified: str  # ex. "site inaccessible", "captcha", "informations insuffisantes"
    platform: Optional[str] = None
    supplier_type: Optional[SupplierType] = None
    moq_detected: Optional[int] = None
    potentially_stale: bool = False  # prix issu d'un résultat de moteur de recherche


class ConnectorReport(BaseModel):
    name: str
    status: str  # "ok" | "degraded" | "error" | "disabled"
    results: int = 0
    verified: int = 0
    error: Optional[str] = None
    duration_ms: int = 0


class SearchFilters(BaseModel):
    brand: Optional[str] = None
    model: Optional[str] = None
    sku: Optional[str] = None
    color: Optional[str] = None
    size: Optional[str] = None
    condition: Optional[str] = None  # "new" | "used" | None (indifférent)
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    country: Optional[str] = None
    # Automobile
    make: Optional[str] = None
    car_model: Optional[str] = None
    year: Optional[int] = None
    part_type: Optional[str] = None
    part_brand: Optional[str] = None
    oem_reference: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    category: Optional[str] = None
    filters: SearchFilters = Field(default_factory=SearchFilters)
    wholesale: bool = False
    deep_search: bool = False
    quantity: Optional[int] = None
    destination_country: str = "FR"
    postal_code: Optional[str] = None
    currency: str = "EUR"


class Diagnostics(BaseModel):
    total_ms: int = 0
    sources_queried: int = 0
    results_detected: int = 0
    offers_verified: int = 0
    leads: int = 0
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class FxInfo(BaseModel):
    base: str = "EUR"
    rates: dict[str, float] = Field(default_factory=dict)
    source: str = "https://api.frankfurter.dev/v1/latest (BCE)"
    fetched_at: datetime = Field(default_factory=now_utc)


class SearchResponse(BaseModel):
    query: str
    category: Optional[str] = None
    destination_country: str
    currency: str
    fx: FxInfo
    verified_offers: list[Offer] = Field(default_factory=list)
    leads: list[Lead] = Field(default_factory=list)
    diagnostics: Diagnostics = Field(default_factory=Diagnostics)
    deep_search_notice: Optional[str] = None
    commercial_warnings: list[str] = Field(default_factory=list)


class ConnectorResult(BaseModel):
    """Résultat brut d'un connecteur, avant vérification."""

    url: str
    title: str = ""
    snippet: str = ""
    connector: str
    is_product_page_guess: bool = False
    price_detected: Optional[float] = None
    currency_detected: Optional[str] = None
    platform: Optional[str] = None
    raw: dict[str, Any] = Field(default_factory=dict)
