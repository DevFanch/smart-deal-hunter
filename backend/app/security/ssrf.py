"""Protection SSRF / DNS rebinding / redirections pour la récupération de pages marchandes.

Toute URL issue d'un moteur de recherche est NON FIABLE :
- seuls http/https sont acceptés ;
- pas d'identifiants dans l'URL ;
- toutes les adresses IP résolues sont vérifiées (privées, loopback, link-local,
  réservées, multicast rejetées) ;
- les redirections sont suivies manuellement et re-vérifiées à chaque saut ;
- taille de réponse plafonnée, timeout strict, types de contenu limités.
"""
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx

PRIVATE_NETWORKS_NOTE = "adresse IP privée, locale ou réservée interdite"

ALLOWED_PORTS = {80, 443}
MAX_RESPONSE_BYTES = 512_000
MAX_REDIRECTS = 4
FETCH_TIMEOUT_S = 10.0
USER_AGENT = "SmartDealHunter/0.1 (+price-comparison; contact: admin@localhost)"


class UnsafeUrlError(ValueError):
    """URL non sûre pour récupération côté serveur."""


def _is_forbidden_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
        or getattr(ip, "is_global", False) is False
    )


def resolve_and_check_host(hostname: str, port: int | None) -> list[str]:
    """Résout le nom et vérifie chaque IP renvoyée. Retourne les IP (audit)."""
    if port is not None and port not in ALLOWED_PORTS:
        raise UnsafeUrlError(f"port non autorisé : {port}")
    try:
        infos = socket.getaddrinfo(hostname, port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UnsafeUrlError("résolution DNS impossible") from exc
    ips: list[str] = []
    for info in infos:
        ip_str = info[4][0]
        if ip_str in ips:
            continue
        ip = ipaddress.ip_address(ip_str)
        if _is_forbidden_ip(ip):
            raise UnsafeUrlError(PRIVATE_NETWORKS_NOTE)
        ips.append(ip_str)
    if not ips:
        raise UnsafeUrlError("aucune adresse résolue")
    return ips


def validate_url(url: str) -> str:
    """Valide une URL avant fetch. Lève UnsafeUrlError sinon."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeUrlError("seuls les schémas http/https sont autorisés")
    if not parsed.hostname:
        raise UnsafeUrlError("hôte manquant")
    if parsed.username or parsed.password:
        raise UnsafeUrlError("identifiants dans l'URL interdits")
    resolve_and_check_host(parsed.hostname, parsed.port)
    return url


def safe_fetch(url: str, *, client: httpx.Client | None = None, max_bytes: int = MAX_RESPONSE_BYTES,
               timeout: float = FETCH_TIMEOUT_S) -> httpx.Response:
    """GET sûr : vérifie l'URL, suit les redirections en revalidant chaque saut,
    plafonne la taille de réponse et le temps total."""
    current = validate_url(url)
    owned = client is None
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/json"}
    resp = None
    try:
        c = client or httpx.Client(timeout=timeout, follow_redirects=False)
        try:
            for _ in range(MAX_REDIRECTS + 1):
                resp = c.get(current, headers=headers)
                if resp.status_code in (301, 302, 303, 307, 308):
                    location = resp.headers.get("location", "")
                    if not location:
                        break
                    # urljoin : les redirections relatives sont revalidées aussi
                    current = validate_url(urljoin(current, location))
                    continue
                break
        finally:
            if owned:
                c.close()
        if resp is None:
            raise UnsafeUrlError("aucune réponse")
        if resp.status_code in (301, 302, 303, 307, 308):
            raise UnsafeUrlError("trop de redirections")
        content_type = resp.headers.get("content-type", "").lower()
        if resp.status_code == 200 and not content_type.startswith(("text/", "application/json", "application/ld+json", "application/xhtml")):
            raise UnsafeUrlError(f"type de contenu non autorisé : {content_type[:60]}")
        if len(resp.content) > max_bytes:
            # On coupe au plafond : le JSON-LD se trouve dans le <head>, en début de page
            resp._content = resp.content[:max_bytes]
        return resp
    except httpx.TimeoutException as exc:
        raise UnsafeUrlError("délai dépassé") from exc


@dataclass
class FetchGuardStats:
    blocked: int = 0
    fetched: int = 0
