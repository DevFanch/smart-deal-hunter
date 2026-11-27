"""Orchestrateur : exécution concurrente des connecteurs, vérification,
normalisation, classement. Un connecteur défaillant n'arrête jamais la recherche."""
from __future__ import annotations

import asyncio
import logging
import time

import httpx

from ..config import settings
from ..fx import convert, get_rates
from ..security.input_sanitizer import sanitize_query
from .connectors.base import BaseConnector, ConnectorOutcome
from .connectors.page_verify import verify_results
from .connectors.websearch import WebSearchConnector
from .connectors.wholesale import WholesaleConnector
from .models import (
    ConnectorResult,
    Diagnostics,
    FxInfo,
    Lead,
    Offer,
    SearchRequest,
    SearchResponse,
    SupplierType,
)
from .normalizer import domain_root, detect_price_and_currency, detect_moq, detect_supplier_type
from .query_builder import WHOLESALE_PLATFORMS
from .ranker import top_verified

logger = logging.getLogger("sdh.orchestrator")

CUSTOMS_WARNING_COUNTRIES = {"CN", "HK", "TW", "SG", "US", "GB"}


class BudgetExceeded(RuntimeError):
    pass


class BudgetTracker:
    """Plafond de dépense des services optionnels. 0 EUR => aucun appel payant."""

    def __init__(self, monthly_budget_eur: float) -> None:
        self.monthly_budget_eur = monthly_budget_eur
        self.spent_eur = 0.0

    def authorize(self, estimated_cost_eur: float) -> bool:
        return self.spent_eur + estimated_cost_eur <= self.monthly_budget_eur


class Orchestrator:
    def __init__(self, connectors: list[BaseConnector] | None = None) -> None:
        self.connectors: list[BaseConnector] = connectors or [
            WebSearchConnector(max_results=settings.max_results_per_source),
            WholesaleConnector(),
        ]
        self.budget = BudgetTracker(settings.monthly_budget_eur)

    async def run(self, request: SearchRequest, client: httpx.AsyncClient) -> SearchResponse:
        start = time.monotonic()
        sanitized = sanitize_query(request.query)
        request.query = sanitized.value
        diagnostics = Diagnostics()
        diagnostics.warnings.extend(sanitized.warnings)

        try:
            fx = await get_rates(client)
        except Exception as exc:  # noqa: BLE001 - interruption FX jamais critique
            logger.warning("taux de change indisponibles: %s", exc)
            fx = FxInfo()
            diagnostics.warnings.append("taux de change indisponibles : comparaison en EUR uniquement")
        target = request.currency.upper() or "EUR"

        plans: list[tuple[BaseConnector, ConnectorOutcome]] = []
        run_connectors = [
            c for c in self.connectors
            if (c.name != "wholesale" or request.wholesale)
        ]
        outcomes = await _gather(run_connectors, request, client)
        plans = list(zip(run_connectors, outcomes))

        all_results: list[ConnectorResult] = []
        for connector, outcome in plans:
            if outcome.report:
                diagnostics.sources_queried += 1
                if outcome.report.error:
                    diagnostics.errors.append(f"{connector.name}: {outcome.report.error}")
                if outcome.disabled_reason:
                    diagnostics.errors.append(outcome.disabled_reason)
            all_results.extend(outcome.results)

        # Déduplication par URL
        unique: dict[str, ConnectorResult] = {}
        for r in all_results:
            key = r.url.split("#")[0]
            unique.setdefault(key, r)
        deduped = list(unique.values())
        diagnostics.results_detected = len(deduped)

        # Vérification réelle des pages les plus prometteuses (client synchrone,
        # exécuté hors de la boucle d'événements)
        try:
            with httpx.Client(timeout=settings.fetch_timeout_s) as sync_client:
                verified, failed = await asyncio.to_thread(
                    verify_results,
                    deduped, request.query, target,
                    lambda a, f, t: convert(fx, a, f, t),
                    sync_client, settings.verify_top_n,
                )
        except Exception as exc:  # noqa: BLE001 - jamais critique
            logger.warning("vérification indisponible: %s", exc)
            verified, failed = [], deduped

        # Données détectées depuis les extraits de recherche (potentiellement obsolètes)
        leads = self._build_leads(failed, request.wholesale)

        # Offres vérifiées : enrichissement fournisseurs si mode grossiste
        if request.wholesale:
            for offer in verified:
                result = unique.get(offer.url.split("#")[0])
                if result and result.platform:
                    offer.platform = result.platform
                    offer.moq = result.raw.get("moq_detected")
                    stype = result.raw.get("supplier_type") or detect_supplier_type(offer.title)
                    offer.supplier_type = SupplierType(stype) if stype else SupplierType.UNKNOWN

        offers = self._apply_filters(verified, request)
        offers = self._apply_quantities(offers, request)

        diagnostics.offers_verified = len(offers)
        diagnostics.leads = len(leads)

        top = top_verified(offers, limit=5)
        warnings = self._commercial_warnings(top, request)

        deep_notice = None
        if request.deep_search:
            deep_notice = self._deep_search_notice()

        diagnostics.total_ms = int((time.monotonic() - start) * 1000)

        return SearchResponse(
            query=request.query,
            category=request.category,
            destination_country=request.destination_country,
            currency=target,
            fx=fx,
            verified_offers=top,
            leads=leads[:20],
            diagnostics=diagnostics,
            deep_search_notice=deep_notice,
            commercial_warnings=warnings,
        )

    def _deep_search_notice(self) -> str:
        if not settings.deep_search_enabled:
            return ("Recherche approfondie non configurée : aucune API payante n'est "
                    "intégrée. La recherche standard gratuite a été exécutée. Pour "
                    "l'activer, configurer SDH_DEEP_SEARCH_PROVIDER et un budget.")
        if not self.budget.authorize(0.01):
            return "Budget mensuel épuisé : recherche approfondie non facturée, standard exécutée."
        return "Recherche approfondie : aucun fournisseur payant configuré, standard exécutée."

    def _build_leads(self, failed: list[ConnectorResult], wholesale: bool) -> list[Lead]:
        leads: list[Lead] = []
        seen: set[str] = set()
        for result in failed:
            url_key = result.url.split("#")[0]
            if url_key in seen:
                continue
            seen.add(url_key)
            reason = str(result.raw.get("reason") or "page produit non consultable")
            price, currency = result.price_detected, result.currency_detected
            if price is None:
                price, currency = detect_price_and_currency(f"{result.title} {result.snippet}")
            leads.append(Lead(
                url=result.url,
                site=domain_root(result.url),
                detected_name=result.title[:300] or "(nom inconnu)",
                detected_sku=None,
                detected_price=price,
                detected_currency=currency,
                source_connector=result.connector,
                reason_not_verified=reason,
                platform=result.platform or next(
                    (label for d, label in WHOLESALE_PLATFORMS.items() if d in domain_root(result.url)), None),
                supplier_type=(SupplierType(result.raw["supplier_type"])
                               if result.raw.get("supplier_type") else None),
                moq_detected=result.raw.get("moq_detected") or detect_moq(f"{result.title} {result.snippet}"),
                potentially_stale=price is not None,
            ))
        return leads

    def _apply_filters(self, offers: list[Offer], request: SearchRequest) -> list[Offer]:
        f = request.filters
        out = []
        for offer in offers:
            if f.price_min is not None and offer.total_cost is not None and offer.total_cost < f.price_min:
                continue
            if f.price_max is not None and offer.total_cost is not None and offer.total_cost > f.price_max:
                continue
            if f.condition == "new" and offer.condition == "used":
                continue
            if f.condition == "used" and offer.condition == "new":
                continue
            if f.brand and f.brand.lower() not in (offer.title or "").lower():
                continue
            out.append(offer)
        return out

    def _apply_quantities(self, offers: list[Offer], request: SearchRequest) -> list[Offer]:
        """Grossistes : ne jamais appliquer un prix par palier non atteint."""
        qty = request.quantity
        if not qty or qty < 1:
            return offers
        for offer in offers:
            offer.quantity_applied = qty
            if offer.moq and qty < offer.moq:
                offer.commercial_terms = (
                    f"Quantité {qty} inférieure au MOQ ({offer.moq}) : offre à recalculer chez le fournisseur.")
        return offers

    def _commercial_warnings(self, offers: list[Offer], request: SearchRequest) -> list[str]:
        warnings: list[str] = []
        if request.wholesale:
            warnings.append(
                "Mode fournisseurs : vérifiez toujours la fiabilité du fournisseur, "
                "le MOQ, les conditions de paiement et les Incoterms avant commande. "
                "Échantillons souvent payants. Aucune fiabilité n'est garantie par Smart Deal Hunter.")
        for offer in offers:
            if (offer.seller_country or "") in CUSTOMS_WARNING_COUNTRIES and request.destination_country.upper() != offer.seller_country:
                warnings.append(
                    f"{offer.shop} : expédition depuis {offer.seller_country} — droits de douane et "
                    f"TVA à l'importation possibles, frais de port non confirmés.")
        if any(o.shipping_status is None or o.total_cost is None for o in offers):
            warnings.append("Certaines offres affichent un coût partiel : frais de port inconnus.")
        # dédoublonnage
        return list(dict.fromkeys(warnings))


async def _gather(connectors: list[BaseConnector], request: SearchRequest,
                  client: httpx.AsyncClient) -> list[ConnectorOutcome]:
    async def run_one(c: BaseConnector) -> ConnectorOutcome:
        return await c.safe_search(request, client)

    import asyncio

    outcomes = await asyncio.gather(*(run_one(c) for c in connectors))
    return list(outcomes)
