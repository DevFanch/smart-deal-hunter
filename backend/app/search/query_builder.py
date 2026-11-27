"""Construction déterministe des variantes de recherche (règles simples, sans IA)."""
from __future__ import annotations

from dataclasses import dataclass, field



# Sources grossistes asiatiques : plateformes ciblées (accès via moteur de
# recherche public ; aucune suppression de protection anti-bot).
WHOLESALE_PLATFORMS = {
    "alibaba.com": "Alibaba",
    "made-in-china.com": "Made-in-China",
    "dhgate.com": "DHgate",
    "aliexpress.com": "AliExpress",
    "globalsources.com": "Global Sources",
}

# Traductions / variantes déterministes utiles pour la recherche internationale
TRANSLATION_HINTS = {
    "chaussures": "shoes",
    "veste": "jacket",
    "manteau": "coat",
    "pull": "sweater",
    "électronique": "electronics",
    "ordinateur": "laptop",
    "machine à café": "coffee machine",
}


@dataclass
class SearchPlan:
    queries: list[str] = field(default_factory=list)
    verify_urls: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


def build_queries(req) -> list[str]:
    """Variantes de recherche : nom exact, marque+modèle, référence, variantes linguistiques."""
    base = req.query.strip()
    f = req.filters
    queries = [base]

    # Marque + modèle si filtres fournis
    if f.brand or f.model:
        combo = " ".join(x for x in (f.brand, f.model) if x)
        if combo:
            queries.insert(0, combo)

    # Référence fabricant / OEM : recherche dédiée en tête (compatibilité prioritaire)
    for ref in (f.sku, f.oem_reference):
        if ref:
            queries.insert(0, ref)

    # Pointure / taille : intégrée quand fournie
    if f.size:
        queries.append(f"{base} {f.size}")

    # État
    if f.condition == "used":
        queries.append(f"{base} occasion")
        queries.append(f"{base} used")

    # Variantes linguistiques déterministes (FR <-> EN)
    lowered = base.lower()
    for fr_word, en_word in TRANSLATION_HINTS.items():
        if fr_word in lowered:
            queries.append(lowered.replace(fr_word, en_word))
        elif en_word in lowered:
            queries.append(lowered.replace(en_word, fr_word))

    return _dedupe(queries)[:6]


def build_wholesale_queries(req) -> list[str]:
    """Recherches grossistes : produit + site:plateforme, et variantes 'wholesale/bulk'."""
    base = req.query.strip()
    qty = req.quantity
    queries = [f"{base} wholesale bulk supplier"]
    for domain in WHOLESALE_PLATFORMS:
        queries.append(f"{base} site:{domain}")
    if qty and qty > 1:
        queries.append(f"{base} wholesale MOQ {qty}")
    return _dedupe(queries)


def deep_search_queries(req) -> list[str]:
    """Niveau 2 (payant, désactivé par défaut) : variantes élargies."""
    base = req.query.strip()
    return _dedupe([
        f"{base} buy online",
        f"{base} meilleur prix 2025",
        f"{base} price comparison",
    ])
