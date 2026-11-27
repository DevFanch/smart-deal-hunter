from app.search.models import MatchLevel, Offer, ShippingStatus
from app.search.ranker import rank_offers, top_verified


def make_offer(name, shop="shop.fr", total=100.0, shipping=ShippingStatus.CONFIRMED,
               level=MatchLevel.EXACT, price=None, availability="en stock", url=None):
    return Offer(
        url=url or f"https://{shop}/x",
        shop=shop,
        title=name,
        price=price if price is not None else total,
        total_cost=total,
        shipping_status=shipping,
        match_level=level,
        availability=availability,
    )


def test_exact_devant_similaire_meme_moins_cher():
    exact = make_offer("Nike Air Max 90", total=120.0, level=MatchLevel.EXACT)
    similaire = make_offer("Baskets running noires", total=40.0, level=MatchLevel.APPROXIMATE)
    ranked = rank_offers([similaire, exact])
    assert ranked[0].title == "Nike Air Max 90"


def test_cout_livre_pris_en_compte():
    a = make_offer("A", total=110.0)
    b = make_offer("B", total=95.0)
    assert rank_offers([a, b])[0].title == "B"


def test_frais_inconnus_jamais_annonces_moins_cher():
    connue = make_offer("livraison connue", total=120.0, shipping=ShippingStatus.CONFIRMED)
    inconnue = make_offer("livraison inconnue", total=100.0, shipping=ShippingStatus.UNKNOWN)
    ranked = rank_offers([inconnue, connue])
    assert ranked[0].title == "livraison connue"


def test_stock_avant_epuise_a_cout_egle():
    epuise = make_offer("E", total=95.0, availability="épuisé")
    stock = make_offer("S", total=95.0, availability="en stock")
    assert rank_offers([epuise, stock])[0].title == "S"


def test_cout_avant_disponibilite_conformement_au_cahier_des_charges():
    epuise_moins_cher = make_offer("E", total=80.0, availability="épuisé")
    stock_plus_cher = make_offer("S", total=120.0, availability="en stock")
    assert rank_offers([epuise_moins_cher, stock_plus_cher])[0].title == "E"


def test_top_ne_jamais_depasser_cinq_ni_inventer():
    offers = [make_offer(f"O{i}", total=100 + i) for i in range(9)]
    assert len(top_verified(offers)) == 5
    assert len(top_verified([make_offer("unique")])) == 1
    assert top_verified([]) == []
