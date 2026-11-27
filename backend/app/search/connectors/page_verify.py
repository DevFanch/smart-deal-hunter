"""Vérification des offres à la source : consultation réelle de la page produit.

- Fetch sûr (protection SSRF, redirections vérifiées, taille/timeout plafonnés).
- Extraction JSON-LD / microdata Schema.org (Product, Offer) + fallback OpenGraph.
- Respect de robots.txt : les chemins interdits ne sont pas consultés.
- Si la page n'est pas consultable (403, CAPTCHA, timeout), le résultat devient
  une PISTE à vérifier, jamais une offre vérifiée.
"""
from __future__ import annotations

import json
import logging
import re
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from ...security.ssrf import UnsafeUrlError, safe_fetch
from ..models import ConnectorResult, Offer, ShippingStatus, now_utc
from .. import normalizer

logger = logging.getLogger("sdh.connectors.page_verify")

JSONLD_RE = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.S | re.I
)
META_OG_RE = re.compile(
    r'<meta[^>]+property=["\']og:(title|price:amount|price:currency)["\'][^>]+content=["\']([^"\']*)["\']', re.I
)
AVAILABILITY_MAP = {
    "https://schema.org/instock": "en stock",
    "https://schema.org/outofstock": "épuisé",
    "https://schema.org/preorder": "précommande",
    "https://schema.org/limitedavailability": "disponibilité limitée",
    "http://schema.org/instock": "en stock",
    "http://schema.org/outofstock": "épuisé",
}
PRICE_REASONS = {
    403: "accès automatisé bloqué (403)",
    429: "limitation de débit (429)",
}

_robots_cache: dict[str, tuple[RobotFileParser | None, float]] = {}
ROBOTS_TTL_S = 1800


def _robots_allowed(url: str) -> bool | None:
    """True/False si robots.txt lisible, None si indéterminé (on tente quand même
    pour un simple GET public, sans jamais contourner une interdiction explicite)."""
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    cached = _robots_cache.get(base)
    import time

    now = time.monotonic()
    if cached and now - cached[1] < ROBOTS_TTL_S:
        rp = cached[0]
    else:
        rp = None
        try:
            resp = httpx.get(f"{base}/robots.txt", timeout=5, follow_redirects=True,
                             headers={"User-Agent": "SmartDealHunter/0.1"})
            if resp.status_code == 200 and len(resp.content) < 100_000:
                rp = RobotFileParser()
                rp.parse(resp.text.splitlines())
        except Exception:  # noqa: BLE001
            rp = None
        _robots_cache[base] = (rp, now)
    if rp is None:
        return None
    try:
        return rp.can_fetch("SmartDealHunter", url) and rp.can_fetch("*", url)
    except Exception:  # noqa: BLE001
        return None


def _as_list(data) -> list:
    if isinstance(data, list):
        return data
    return [data]


def _first_product(graph) -> dict | None:
    for node in _as_list(graph):
        if not isinstance(node, dict):
            continue
        types = node.get("@type") or []
        if isinstance(types, str):
            types = [types]
        if any(t.lower() == "product" for t in types):
            return node
        # "@graph" imbriqué
        sub = node.get("@graph")
        if sub:
            found = _first_product(sub)
            if found:
                return found
    return None


def extract_product_jsonld(html: str) -> dict | None:
    for block in JSONLD_RE.findall(html):
        text = block.strip()
        if not text:
            continue
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            continue
        found = _first_product(data)
        if found:
            return found
    return None


def _extract_offers(product: dict) -> list[dict]:
    offers = product.get("offers") or []
    if isinstance(offers, dict):
        offers = [offers]
    result = []
    for o in offers:
        if isinstance(o, dict):
            result.append(o)
    return result


def parse_page_to_offer(result: ConnectorResult, html: str, final_url: str, query: str,
                        target_currency: str, fx_convert) -> tuple[Offer | None, str | None]:
    """Convertit une page consultée en offre vérifiée, ou retourne un motif d'échec."""
    product = extract_product_jsonld(html)
    og = dict(META_OG_RE.findall(html))
    title = (product or {}).get("name") or og.get("title") or result.title or ""
    if not title:
        return None, "informations insuffisantes (pas de nom produit)"

    offers = _extract_offers(product or {})
    price = currency = sku = availability = None
    condition = None
    image_url = None
    if product:
        sku = product.get("sku") or product.get("gtin13")
        image = product.get("image")
        if isinstance(image, list) and image:
            image = image[0]
        if isinstance(image, str):
            image_url = image[:500]
        best = None
        for o in offers:
            p = o.get("price") if o.get("price") is not None else o.get("lowPrice")
            if p is not None:
                try:
                    if best is None or float(p) < best[0]:
                        best = (float(p), o.get("priceCurrency"))
                except (TypeError, ValueError):
                    continue
        if best:
            price, currency = best[0], best[1]
            availability = AVAILABILITY_MAP.get(
                str(offers[0].get("availability", "")), None)
            item_condition = str(offers[0].get("itemCondition", "") or product.get("itemCondition", ""))
            if "usedcondition" in item_condition.lower():
                condition = "used"
            elif "newcondition" in item_condition.lower():
                condition = "new"
    if price is None:
        m = og.get("price:amount")
        if m:
            try:
                price = float(m.replace(",", "."))
                currency = og.get("price:currency") or None
            except ValueError:
                pass
    if price is None and result.price_detected is not None:
        price = result.price_detected
        currency = result.currency_detected

    # Une offre vérifiée sans prix exploitable est inutile : piste avec motif
    if price is None or price <= 0:
        return None, "prix non disponible sur la page consultée"

    # Niveau de correspondance sur le titre réel de la page
    level, reason = normalizer.match_level(query, title)
    if level == normalizer.MatchLevel.UNCONFIRMED:
        return None, "produit non correspondant"

    seller_country = normalizer.guess_seller_country(final_url)
    converted, original_currency = None, currency
    if price is not None:
        converted = fx_convert(price, currency or "EUR", target_currency)

    shipping = None
    shipping_status = ShippingStatus.UNKNOWN
    total = None
    if converted is not None:
        total = converted  # coût partiel : avertissement géré par le front
    if shipping is None and shipping_status == ShippingStatus.UNKNOWN:
        total = converted  # inchangé : frais inconnus ne sont jamais inventés

    return Offer(
        url=final_url,
        shop=normalizer.domain_root(final_url),
        title=title[:300],
        brand=(product or {}).get("brand", {}).get("name") if isinstance((product or {}).get("brand"), dict) else (product or {}).get("brand"),
        sku=sku,
        image_url=image_url,
        price=price,
        currency=currency,
        original_currency=original_currency,
        shipping_cost=None,
        shipping_status=shipping_status,
        total_cost=total,
        condition=condition,
        availability=availability,
        seller_country=seller_country,
        match_level=level,
        match_reason=reason,
        verified=True,
        checked_at=now_utc(),
        source_connector=result.connector,
    ), None


def verify_results(results: list[ConnectorResult], query: str, target_currency: str,
                   fx_convert, client: httpx.Client, max_verify: int = 8
                   ) -> tuple[list[Offer], list[ConnectorResult]]:
    """Consulte les pages candidates et sépare offres vérifiées / non vérifiables.

    Retourne (offres_vérifiées, résultats_échoués) ; les échecs redeviennent des pistes.
    """
    verified: list[Offer] = []
    failed: list[ConnectorResult] = []
    seen_urls: set[str] = set()
    for result in results[:max_verify]:
        url = result.url.split("#")[0]
        if url in seen_urls:
            continue
        seen_urls.add(url)
        if _robots_allowed(url) is False:
            result.raw["reason"] = "interdit par robots.txt"
            failed.append(result)
            continue
        try:
            resp = safe_fetch(url, client=client)
        except UnsafeUrlError as exc:
            result.raw["reason"] = str(exc)
            failed.append(result)
            continue
        if resp.status_code != 200:
            result.raw["reason"] = PRICE_REASONS.get(resp.status_code, f"page non consultable (HTTP {resp.status_code})")
            failed.append(result)
            continue
        body = resp.text
        if "captcha" in body[:4000].lower() or "cf-challenge" in body[:4000].lower():
            result.raw["reason"] = "captcha / protection anti-bot"
            failed.append(result)
            continue
        offer, reason = parse_page_to_offer(
            result, body, str(resp.url), query, target_currency, fx_convert)
        if offer:
            verified.append(offer)
        else:
            result.raw["reason"] = reason or "informations insuffisantes"
            failed.append(result)
    return verified, failed
