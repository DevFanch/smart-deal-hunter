"""Connecteur Serper.dev (Google Search + Shopping).

- Inscription gratuite, 2 500 requêtes offertes sans carte bancaire.
- Utilisé en niveau 1 UNIQUEMENT si une clé est configurée ; jamais d'appel
  facturé : un compteur de quota strict coupe le connecteur dès que le quota
  gratuit est épuisé (par défaut 2 500 requêtes, une requête = un crédit).
"""
from __future__ import annotations



import httpx

from ..models import ConnectorResult, SearchRequest
from .. import normalizer
from .base import BaseConnector, ConnectorOutcome


class SerperQuotaExhausted(RuntimeError):
    pass


class SerperConnector(BaseConnector):
    name = "serper"
    enabled = False  # activé uniquement si une clé est fournie

    API_URL = "https://google.serper.dev/search"

    def __init__(self, api_key: str | None = None, quota_total: int = 2500) -> None:
        self.api_key = (api_key or "").strip()
        self.quota_total = max(0, quota_total)
        self.quota_used = 0
        if self.api_key and self.quota_total > 0:
            self.enabled = True

    @property
    def quota_remaining(self) -> int:
        return max(0, self.quota_total - self.quota_used)

    def _reserve(self) -> None:
        if not self.enabled:
            raise SerperQuotaExhausted("clé absente ou quota épuisé")
        if self.quota_used >= self.quota_total:
            raise SerperQuotaExhausted(
                f"quota gratuit Serper épuisé ({self.quota_used}/{self.quota_total}) : connecteur arrêté, aucune facturation")

    def _parse(self, data: dict, country: str) -> list[ConnectorResult]:
        results: list[ConnectorResult] = []
        # Résultats shopping : prix structuré quand fourni
        for item in data.get("shopping", [])[:8]:
            link = (item.get("link") or "").strip()
            if not link.startswith(("http://", "https://")):
                continue
            price, currency = None, None
            raw_price = item.get("price")
            if raw_price:
                price, currency = normalizer.detect_price_and_currency(str(raw_price))
            results.append(ConnectorResult(
                url=link,
                title=str(item.get("title", ""))[:300],
                snippet=str(item.get("source", ""))[:200],
                connector=self.name,
                is_product_page_guess=True,
                price_detected=price,
                currency_detected=currency,
                raw={"kind": "shopping", "gl": country},
            ))
        # Résultats organiques
        for item in data.get("organic", [])[:8]:
            link = (item.get("link") or "").strip()
            if not link.startswith(("http://", "https://")):
                continue
            text = f"{item.get('title', '')} {item.get('snippet', '')}"
            price, currency = normalizer.detect_price_and_currency(text)
            results.append(ConnectorResult(
                url=link,
                title=str(item.get("title", ""))[:300],
                snippet=str(item.get("snippet", ""))[:500],
                connector=self.name,
                is_product_page_guess=True,
                price_detected=price,
                currency_detected=currency,
                raw={"kind": "organic", "gl": country},
            ))
        return results

    async def search(self, request: SearchRequest, client: httpx.AsyncClient) -> ConnectorOutcome:
        self._reserve()
        payload = {
            "q": request.query,
            "num": 10,
            "gl": (request.destination_country or "fr").lower(),
            "hl": "fr",
        }
        resp = await client.post(
            self.API_URL,
            headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
            json=payload,
        )
        if resp.status_code == 403:
            raise RuntimeError("clé Serper invalide (HTTP 403)")
        if resp.status_code == 429:
            raise SerperQuotaExhausted("limitation Serper (429) : connecteur arrêté")
        resp.raise_for_status()
        self.quota_used += 1
        data = resp.json()
        return ConnectorOutcome(results=self._parse(data, payload["gl"]))
