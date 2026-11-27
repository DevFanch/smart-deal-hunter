from app.search.models import MatchLevel
from app.search.normalizer import (
    detect_condition,
    detect_moq,
    detect_price_and_currency,
    detect_supplier_type,
    guess_seller_country,
    match_level,
    normalize_text,
)


def test_normalisation_minuscules_sans_accents():
    assert normalize_text("Chaussures ÉTÉ Spéciales") == "chaussures ete speciales"


def test_correspondance_exacte():
    level, _ = match_level("Nike Air Max 90", "Nike Air Max 90 Homme - Noir")
    assert level == MatchLevel.EXACT


def test_correspondance_probable():
    level, _ = match_level("Nike Air Max 90 EU 42", "Nike Air Max 90 Essential")
    assert level in (MatchLevel.PROBABLE, MatchLevel.EXACT)


def test_produit_similaire_mamie_jamais_exact():
    level, _ = match_level("Nike Air Max 90", "Adidas Samba OG")
    assert level in (MatchLevel.APPROXIMATE, MatchLevel.UNCONFIRMED)


def test_prix_eur_detecte():
    assert detect_price_and_currency("Prix: 129,99 € livraison incluse") == (129.99, "EUR")
    assert detect_price_and_currency("EUR 89.90") == (89.90, "EUR")


def test_prix_usd_detecte():
    assert detect_price_and_currency("Price: $120.00") == (120.00, "USD")


def test_prix_absent():
    assert detect_price_and_currency("aucun prix ici") == (None, None)


def test_moq_detecte():
    assert detect_moq("MOQ: 12 pieces") == 12
    assert detect_moq("Min. Order = 50 pcs") == 50
    assert detect_moq("aucune contrainte") is None


def test_type_fournisseur():
    assert detect_supplier_type("Shenzhen XYZ Manufacturer Co Ltd") == "fabricant"
    assert detect_supplier_type("Wholesale supplier Europe") == "grossiste"
    assert detect_supplier_type("Trading company") == "intermediaire"


def test_condition_detectee():
    assert detect_condition("Nike Air Max 90 occasion") == "used"
    assert detect_condition("Brand new sealed") == "new"


def test_pays_vendeur_depuis_tld():
    assert guess_seller_country("https://www.fnac.com/x") == "FR"
    assert guess_seller_country("https://shop.de/y") == "DE"
    assert guess_seller_country("https://alibaba.com/z") == "CN"
