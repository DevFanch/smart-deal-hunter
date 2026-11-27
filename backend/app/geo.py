"""Géolocalisation approximative par IP : uniquement pour deviner le pays de
destination par défaut. Aucune adresse IP brute n'est stockée (cache mémoire
court, clé anonymisée, seulement le code pays est mémorisé)."""
from __future__ import annotations

import hashlib
import time

import httpx

from .config import settings

_cache: dict[str, tuple[str, float]] = {}


def _anon_key(ip: str) -> str:
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


async def guess_country(client_ip: str | None, client: httpx.AsyncClient) -> str:
    """Pays de destination par défaut. Échec silencieux -> défaut configuré (FR)."""
    if not client_ip or not settings.geoip_enabled:
        return settings.default_country
    # IP privée / locale (dev, docker, LAN) : inutile d'interroger un service externe
    if client_ip.startswith(("10.", "192.168.", "172.16.", "172.17.", "172.18.",
                             "172.19.", "172.2", "172.30.", "172.31.", "127.", "::1")):
        return settings.default_country
    key = _anon_key(client_ip)
    cached = _cache.get(key)
    if cached and time.monotonic() - cached[1] < settings.geoip_cache_ttl_s:
        return cached[0]
    try:
        resp = await client.get(settings.geoip_url.format(ip=client_ip), timeout=4)
        code = str(resp.json().get("countryCode", "")).upper()
        if len(code) == 2:
            _cache[key] = (code, time.monotonic())
            return code
    except Exception:  # noqa: BLE001
        pass
    return settings.default_country
