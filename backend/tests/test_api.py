"""Tests API : rejets de sécurité, limites, endpoints métadonnées."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_meta():
    r = client.get("/api/meta")
    assert r.status_code == 200
    body = r.json()
    assert "Chaussures" in body["categories"]
    assert body["max_query_length"] == 160


def test_requete_avec_script_rejetee():
    r = client.post("/api/search", json={"query": "<script>alert(1)</script>"})
    assert r.status_code == 422
    assert r.json()["error"] == "invalid_query"


def test_requete_trop_longue_rejetee():
    r = client.post("/api/search", json={"query": "a" * 200})
    assert r.status_code == 422


def test_requete_vide_rejetee():
    r = client.post("/api/search", json={"query": "   "})
    assert r.status_code == 422


def test_code_postal_invalide_rejete():
    r = client.post("/api/search", json={"query": "Nike", "postal_code": "DROP TABLE users;--"})
    assert r.status_code == 422


def test_code_postal_valide_accepte_au_niveau_validation():
    # La recherche elle-même nécessite le réseau (connecteurs) ; on vérifie ici
    # uniquement que la validation d'entrée passe.
    from app.security.input_sanitizer import sanitize_query
    assert sanitize_query("75011 Paris").value == "75011 Paris"


def test_rate_limiting():
    from app.security.rate_limit import RateLimiter
    limiter = RateLimiter(max_requests=3, window_s=60)

    class FakeRequest:
        headers = {"x-forwarded-for": "203.0.113.9"}
        client = None
        url = type("U", (), {"path": "/api/search"})()

    for _ in range(3):
        assert limiter.check(FakeRequest())
    assert not limiter.check(FakeRequest())
