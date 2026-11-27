"""Tests connecteur Serper : parsing, quota strict, réactivité aux erreurs."""
import pytest

from app.search.connectors.serper_connector import SerperConnector, SerperQuotaExhausted


SHOPPING_DATA = {
    "shopping": [
        {
            "title": "Nike Air Max 90 Men's Shoes",
            "link": "https://www.nike.com/t/air-max-90-xYz",
            "price": "$129.99",
            "source": "nike.com",
        },
        {
            "title": "Nike Air Max 90",
            "link": "not-a-url",
            "price": "€99,00",
        },
    ],
    "organic": [
        {
            "title": "Air Max 90 pas cher - Zalando",
            "link": "https://www.zalando.fr/nike-air-max-90.html",
            "snippet": "Livraison gratuite dès 25 € — prix 119,90 €",
        },
    ],
}


def test_parse_shopping_prix_detecte():
    connector = SerperConnector("fake-key", quota_total=10)
    results = connector._parse(SHOPPING_DATA, "fr")
    kinds = {r.raw["kind"] for r in results}
    assert kinds == {"shopping", "organic"}
    shopping = [r for r in results if r.raw["kind"] == "shopping"]
    assert shopping[0].price_detected == 129.99
    assert shopping[0].currency_detected == "USD"
    # Lien non http écarté
    assert all(r.url.startswith("http") for r in results)


def test_sans_cle_connecteur_inactif():
    connector = SerperConnector(None)
    assert connector.enabled is False  # aucune clé : jamais actif


def test_quota_epuise_bloque_et_ne_facture_pas():
    connector = SerperConnector("fake-key", quota_total=2)
    connector._reserve()
    connector.quota_used = 2
    with pytest.raises(SerperQuotaExhausted):
        connector._reserve()
    assert connector.quota_used == 2  # aucune réservation au-delà du quota


def test_prix_europeen_format_fr():
    connector = SerperConnector("fake-key", quota_total=10)
    results = connector._parse({"shopping": [{"title": "X", "link": "https://a.fr/p", "price": "129,99 €"}]}, "fr")
    assert results[0].price_detected == 129.99
    assert results[0].currency_detected == "EUR"
