"""Normalisation et comparaison des libellés produits (règles déterministes, sans IA)."""
from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse

from .models import MatchLevel

STOPWORDS_FR_EN = {
    "acheter", "achat", "prix", "pas", "cher", "meilleur", "buy", "price", "best",
    "the", "le", "la", "les", "de", "du", "des", "a", "à", "au", "aux", "en",
    "for", "with", "and", "et", "of", "pour", "neuf", "occasion", "new", "used",
    "sans", "frais", "livraison", "free", "shipping", "pro", "promo", "vente",
}


def normalize_text(text: str) -> str:
    """Minuscules, accents retirés, ponctuation -> espace, espaces collapsés."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"[^\w\s#+/]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def significant_tokens(text: str) -> set[str]:
    """Jetons significatifs (hors mots courants e-commerce)."""
    tokens = set()
    for tok in normalize_text(text).split():
        if len(tok) < 2 and not tok.isdigit():
            continue
        if tok in STOPWORDS_FR_EN:
            continue
        tokens.add(tok)
    return tokens


def match_level(query: str, candidate: str) -> tuple[MatchLevel, str]:
    """Niveau de correspondance explicite entre la recherche et un libellé produit.

    - exacte         : tous les jetons significatifs de la recherche sont présents
                       (y compris les jetons à 1 caractère purement numériques, ex. "90")
    - tres_probable  : >= 60 % des jetons significatifs présents
    - approximative  : au moins un jeton présent
    - non_confirmee  : aucun jeton pertinent retrouvé
    """
    q_tokens = significant_tokens(query)
    if not q_tokens:
        return MatchLevel.UNCONFIRMED, "recherche non exploitable"
    c_tokens = significant_tokens(candidate)
    missing = q_tokens - c_tokens
    present = q_tokens & c_tokens
    ratio = len(present) / len(q_tokens)
    if not missing:
        return MatchLevel.EXACT, "tous les termes du produit sont présents"
    if ratio >= 0.6:
        return MatchLevel.PROBABLE, f"{len(present)}/{len(q_tokens)} termes présents (manque: {', '.join(sorted(missing))[:40]})"
    if present:
        return MatchLevel.APPROXIMATE, f"{len(present)}/{len(q_tokens)} termes présents (produit similaire)"
    return MatchLevel.UNCONFIRMED, "aucun terme de la recherche retrouvé"


def domain_root(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


COUNTRY_FROM_TLD = {
    "fr": "FR", "de": "DE", "es": "ES", "it": "IT", "be": "BE", "nl": "NL",
    "pt": "PT", "at": "AT", "ie": "IE", "pl": "PL", "uk": "GB", "eu": "EU",
    "us": "US", "ca": "CA", "cn": "CN", "hk": "HK", "jp": "JP", "ch": "CH",
}


KNOWN_DOMAIN_COUNTRY = {
    "fnac.com": "FR", "darty.com": "FR", "boulanger.com": "FR", "ldlc.com": "FR",
    "decathlon.fr": "FR", "amazon.fr": "FR", "amazon.de": "DE", "amazon.co.uk": "GB",
    "amazon.com": "US", "alibaba.com": "CN", "aliexpress.com": "CN", "dhgate.com": "CN",
    "made-in-china.com": "CN", "globalsources.com": "HK", "patagonia.com": "US",
}


def guess_seller_country(url: str) -> str | None:
    host = domain_root(url)
    if host in KNOWN_DOMAIN_COUNTRY:
        return KNOWN_DOMAIN_COUNTRY[host]
    tld = host.rsplit(".", 1)[-1]
    return COUNTRY_FROM_TLD.get(tld)


PRICE_PATTERNS = [
    re.compile(r"(?:€|eur)\s*([0-9]+(?:[.,][0-9]{1,2})?)", re.I),
    re.compile(r"([0-9]+(?:[.,][0-9]{1,2})?)\s*(?:€|eur)\s*$|([0-9]+(?:[.,][0-9]{1,2})?)\s*€", re.I),
    re.compile(r"\$\s*([0-9]+(?:[.,][0-9]{1,2})?)"),
    re.compile(r"(?:£|gbp)\s*([0-9]+(?:[.,][0-9]{1,2})?)", re.I),
    re.compile(r"([0-9]+(?:[.,][0-9]{1,2})?)\s*(?:£|gbp)", re.I),
]


def detect_price_and_currency(text: str) -> tuple[float | None, str | None]:
    """Détecte un prix et sa devise dans un texte libre. Jamais une garantie : à confirmer."""
    for i, pattern in enumerate(PRICE_PATTERNS):
        m = pattern.search(text)
        if m:
            raw = next((g for g in m.groups() if g is not None), m.group(1))
            raw = str(raw).replace(",", ".")
            try:
                price = float(raw)
            except ValueError:
                continue
            if 0.01 <= price <= 1_000_000:
                currency = ("EUR", "EUR", "USD", "GBP", "GBP")[i]
                return price, currency
    return None, None


MOQ_PATTERN = re.compile(r"(?:moq|min\.?\s*order)\s*[:=]?\s*(\d[\d\s,]*)\s*(pieces?|pcs?|units?|paires?|pairs?)?", re.I)


def detect_moq(text: str) -> int | None:
    m = MOQ_PATTERN.search(text)
    if m:
        try:
            value = int(m.group(1).replace(" ", "").replace(",", ""))
            if 0 < value <= 1_000_000:
                return value
        except ValueError:
            pass
    return None


SUPPLIER_TYPE_HINTS = [
    (re.compile(r"\b(manufacturer|usine|factory|oem/odm)\b", re.I), "fabricant"),
    (re.compile(r"\b(wholesaler|grossiste|wholesale supplier)\b", re.I), "grossiste"),
    (re.compile(r"\b(distributor|distributeur)\b", re.I), "distributeur"),
    (re.compile(r"\b(trading company|intermediar|agent|dropship)\b", re.I), "intermediaire"),
]


def detect_supplier_type(text: str) -> str | None:
    for pattern, label in SUPPLIER_TYPE_HINTS:
        if pattern.search(text):
            return label
    return None


CONDITION_PATTERNS = [
    (re.compile(r"\b(occasion|used|second[- ]?hand|reconditioned|refurbished)\b", re.I), "used"),
    (re.compile(r"\b(neuf|new|brand new)\b", re.I), "new"),
]


def detect_condition(text: str) -> str | None:
    for pattern, label in CONDITION_PATTERNS:
        if pattern.search(text):
            return label
    return None
