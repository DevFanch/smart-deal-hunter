"""Tests d'intégration de l'orchestrateur avec connecteurs factices (hors réseau)."""
import pytest

from app.search.connectors.base import BaseConnector, ConnectorOutcome
from app.search.models import ConnectorResult, SearchRequest
from app.search.orchestrator import Orchestrator
from app.search.models import SearchFilters


class FakeConnector(BaseConnector):
    name = "fake"

    def __init__(self, results):
        self._results = results

    async def search(self, request, client):
        return ConnectorOutcome(results=self._results)


class ExplodingConnector(BaseConnector):
    name = "explosive"

    async def search(self, request, client):
        raise RuntimeError("source indisponible")


def make_result(url, title):
    return ConnectorResult(url=url, title=title, connector="fake", is_product_page_guess=True)


def test_connecteur_defaillant_ne_fait_pas_echouer():
    orchestrator = Orchestrator(connectors=[ExplodingConnector(), FakeConnector([])])
    request = SearchRequest(query="Nike Air Max 90", destination_country="FR")
    import httpx, asyncio

    async def run():
        async with httpx.AsyncClient() as client:
            return await orchestrator.run(request, client)

    response = asyncio.run(run())
    assert any("explosive" in e for e in response.diagnostics.errors)


def test_site_inaccessible_devient_piste():
    # URL privée : bloquée par le garde SSRF -> piste, jamais une offre vérifiée
    orchestrator = Orchestrator(connectors=[FakeConnector([make_result("http://127.0.0.1:9/x", "Nike Air Max 90")])])
    request = SearchRequest(query="Nike Air Max 90", destination_country="FR")
    import httpx, asyncio

    async def run():
        async with httpx.AsyncClient() as client:
            return await orchestrator.run(request, client)

    response = asyncio.run(run())
    assert response.verified_offers == []
    assert len(response.leads) == 1
    assert response.leads[0].reason_not_verified


def test_filtres_prix_et_etat():
    orchestrator = Orchestrator(connectors=[])
    from app.search.models import Offer, MatchLevel, ShippingStatus

    o1 = Offer(url="https://a.fr/1", shop="a.fr", title="X", total_cost=50.0, price=45.0,
               match_level=MatchLevel.EXACT, shipping_status=ShippingStatus.CONFIRMED, condition="used")
    o2 = Offer(url="https://a.fr/2", shop="a.fr", title="X", total_cost=95.0, price=90.0,
               match_level=MatchLevel.EXACT, shipping_status=ShippingStatus.CONFIRMED, condition="new")
    request = SearchRequest(query="X", filters=SearchFilters(price_max=100, condition="new"))
    filtered = orchestrator._apply_filters([o1, o2], request)
    assert [o.url for o in filtered] == ["https://a.fr/2"]


def test_quantite_inferieure_au_moq_signalee():
    orchestrator = Orchestrator(connectors=[])
    from app.search.models import Offer, MatchLevel

    o = Offer(url="https://alibaba.com/1", shop="alibaba.com", title="sneakers",
              match_level=MatchLevel.EXACT, moq=50)
    request = SearchRequest(query="sneakers", wholesale=True, quantity=12)
    orchestrator._apply_quantities([o], request)
    assert "MOQ" in (o.commercial_terms or "")


def test_avertissements_importation_asie():
    orchestrator = Orchestrator(connectors=[])
    from app.search.models import Offer, MatchLevel

    o = Offer(url="https://alibaba.com/p", shop="alibaba.com", title="sneakers bulk",
              match_level=MatchLevel.EXACT, seller_country="CN")
    warnings = orchestrator._commercial_warnings([o], SearchRequest(query="s", destination_country="FR"))
    assert any("douane" in w.lower() for w in warnings)
