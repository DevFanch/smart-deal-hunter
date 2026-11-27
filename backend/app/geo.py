"""Géolocalisation approximative par IP : uniquement pour deviner le pays de
destination par défaut. Aucune adresse IP brute n'est stockée (cache mémoire
court, clé anonymisée, seulement le code pays est mémorisé)."""
from __future__ import annotations

import hashlib
import os
import time

import httpx

from .config import settings

_cache: dict[str, tuple[str, float]] = {}

_MAXMIND_READER = None
_MAXMIND_PATH = None


def _local_country(ip: str) -> str | None:
    """Lookup GeoLite2 local (MaxMind) si la base est présente : zéro réseau."""
    global _MAXMIND_READER, _MAXMIND_PATH
    path = settings.geoip_db_path
    if not path or not os.path.isfile(path):
        return None
    try:
        if _MAXMIND_READER is None or _MAXMIND_PATH != path:
            import maxminddb

            _MAXMIND_READER = maxminddb.open(path)
            _MAXMIND_PATH = path
        record = _MAXMIND_READER.get(ip) or {}
        code = (record.get("country") or {}).get("iso_code")
        return str(code).upper() if code else None
    except Exception:  # noqa: BLE001 - la géoloc ne doit jamais casser la recherche
        return None


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
    # 1) base locale MaxMind si configurée (aucun réseau, aucune limite de débit)
    local = _local_country(client_ip)
    if local:
        return local
    # 2) service gratuit ip-api en secours
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
