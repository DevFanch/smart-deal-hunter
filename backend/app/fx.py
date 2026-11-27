"""Taux de change : source identifiée et horodatée (BCE via frankfurter.dev, gratuit).

Convertit les prix dans une devise commune de comparaison tout en conservant la
devise originale de chaque offre.
"""
from __future__ import annotations

import time

import httpx

from .config import settings
from .search.models import FxInfo

_cache: dict[str, tuple[FxInfo, float]] = {}


class FxError(RuntimeError):
    pass


async def _fetch_rates(client: httpx.AsyncClient) -> FxInfo:
    resp = await client.get(settings.fx_api_url, params={"base": "EUR"})
    resp.raise_for_status()
    data = resp.json()
    if "rates" not in data:
        raise FxError("réponse FX inattendue")
    rates = {k.upper(): float(v) for k, v in data["rates"].items()}
    rates["EUR"] = 1.0
    return FxInfo(base="EUR", rates=rates)


async def get_rates(client: httpx.AsyncClient) -> FxInfo:
    cached = _cache.get("latest")
    if cached and time.monotonic() - cached[1] < settings.fx_cache_ttl_s:
        return cached[0]
    try:
        info = await _fetch_rates(client)
        _cache["latest"] = (info, time.monotonic())
        return info
    except Exception as exc:  # noqa: BLE001
        if cached:
            return cached[0]  # périmé mais disponible : mieux que rien
        raise FxError(f"taux de change indisponibles: {exc}") from exc


def convert(info: FxInfo, amount: float, from_currency: str, to_currency: str) -> float | None:
    """Conversion transparente via les taux horodatés. Retourne None si inconnu."""
    from_currency = (from_currency or "EUR").upper()
    to_currency = (to_currency or "EUR").upper()
    if from_currency == to_currency:
        return round(amount, 2)
    if from_currency not in info.rates or to_currency not in info.rates:
        return None
    eur_value = amount / info.rates[from_currency]
    return round(eur_value * info.rates[to_currency], 2)
