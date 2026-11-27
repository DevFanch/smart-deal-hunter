"""Classement transparent, sans score arbitraire.

Priorités : correspondance exacte > coût total livré connu > fiabilité source >
disponibilité > fraîcheur. Une offre dont les frais de port sont inconnus n'est
JAMAIS classée comme la moins chère livrée.
"""
from __future__ import annotations

from .models import MatchLevel, Offer, ShippingStatus

MATCH_RANK = {
    MatchLevel.EXACT: 0,
    MatchLevel.PROBABLE: 1,
    MatchLevel.APPROXIMATE: 2,
    MatchLevel.UNCONFIRMED: 3,
}

SOURCE_RELIABILITY_RANK = {
    # site officiel de marque > grand distributeur connu > autres
    "patagonia.com": 0, "nike.com": 0, "adidas.com": 0, "samsung.com": 0,
    "decathlon.fr": 1, "darty.com": 1, "fnac.com": 1, "amazon.fr": 1, "amazon.com": 1,
    "amazon.de": 1, "amazon.co.uk": 1, "boulanger.com": 1, "ldlc.com": 1,
}
DEFAULT_RELIABILITY = 2

AVAILABILITY_RANK = {"en stock": 0, "disponibilité limitée": 1, "précommande": 2, "épuisé": 3}


def _total_cost_key(offer: Offer) -> tuple[int, float]:
    """(0, coût) si coût total livré connu, sinon (1, prix unitaire) — les offres
    au coût inconnu sont toujours placées après les coûts connus au même niveau
    de correspondance."""
    if offer.shipping_status != ShippingStatus.UNKNOWN and offer.total_cost is not None:
        return (0, offer.total_cost)
    if offer.shipping_status == ShippingStatus.UNKNOWN and offer.total_cost is not None:
        return (1, offer.total_cost)
    return (2, offer.price or 10**9)


def sort_key(offer: Offer, sort_mode: str = "best_delivered") -> tuple:
    match = MATCH_RANK.get(offer.match_level, 3)
    reliability = SOURCE_RELIABILITY_RANK.get(offer.shop or "", DEFAULT_RELIABILITY)
    availability = AVAILABILITY_RANK.get((offer.availability or "").lower(), 2)
    price_key = _total_cost_key(offer)

    if sort_mode == "price_only":
        # Prix produit seul : les correspondances non confirmées restent derrière
        return (match, price_key[1] if price_key[0] < 2 else 10**9, reliability, availability)
    if sort_mode == "best_match":
        return (match, reliability, price_key, availability)
    if sort_mode == "best_compromise":
        return (match, (price_key[0], min(price_key[1], 10**9) / 1000 + reliability), availability)
    # défaut : meilleur prix livré
    return (match, price_key, reliability, availability)


def rank_offers(offers: list[Offer], sort_mode: str = "best_delivered") -> list[Offer]:
    return sorted(offers, key=lambda o: sort_key(o, sort_mode))


def top_verified(offers: list[Offer], limit: int = 5, sort_mode: str = "best_delivered") -> list[Offer]:
    """Top N des offres vérifiées. Jamais complété artificiellement."""
    return rank_offers(offers, sort_mode)[:limit]
