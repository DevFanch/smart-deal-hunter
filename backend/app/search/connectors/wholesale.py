"""Connecteur grossistes / fournisseurs asiatiques (niveau 1, gratuit).

- Interroge les moteurs publics vers les plateformes professionnelles
  (Alibaba, Made-in-China, DHgate, AliExpress, Global Sources).
- Aucun scraping direct des plateformes : leurs CGU l'interdisent et elles sont
  protégées par anti-bot. Les plateformes sont donc des PISTES, sauf si la page
  est effectivement consultable et contient des données structurées.
- MOQ et paliers de prix extraits uniquement quand ils sont présents dans les
  données réellement accessibles (titre, extrait, JSON-LD).
- Aucune contrefaçon : les termes "replica", "fake", "1:1" dans le titre/extrait
  écartent le résultat.
"""
from __future__ import annotations

import asyncio
import re

from ddgs import DDGS

from ..models import ConnectorResult, SearchRequest
from ..query_builder import WHOLESALE_PLATFORMS
from .. import normalizer
from .base import BaseConnector, ConnectorOutcome
from .websearch import BACKENDS

COUNTERFEIT_PATTERN = re.compile(
    r"\b(replica|rep(\s|l)?|fake|copy\s+1:1|1:1\s+copy|counterfeit|knockoff|bootleg)\b", re.I
)
B2B_DOMAINS = set(WHOLESALE_PLATFORMS)


class WholesaleConnector(BaseConnector):
    name = "wholesale"
    enabled = True

    def _run_sync(self, queries: list[str], max_results: int) -> list[ConnectorResult]:
        results: list[ConnectorResult] = []
        for query in queries[:5]:
            for backend in BACKENDS:
                try:
                    hits = DDGS().text(query, max_results=6, backend=backend)
                except Exception:
                    continue
                for hit in hits:
                    url = (hit.get("href") or "").strip()
                    if not url.startswith(("http://", "https://")):
                        continue
                    domain = normalizer.domain_root(url)
                    platform = next((label for d, label in WHOLESALE_PLATFORMS.items() if d in domain), None)
                    text = f"{hit.get('title', '')} {hit.get('body', '')}"
                    if COUNTERFEIT_PATTERN.search(text):
                        continue  # contrefaçon : exclu
                    if platform is None and domain not in B2B_DOMAINS and "wholesale" not in text.lower():
                        continue  # hors périmètre B2B
                    moq = normalizer.detect_moq(text)
                    price, currency = normalizer.detect_price_and_currency(text)
                    results.append(ConnectorResult(
                        url=url,
                        title=(hit.get("title") or "")[:300],
                        snippet=(hit.get("body") or "")[:500],
                        connector=self.name,
                        price_detected=price,
                        currency_detected=currency,
                        platform=platform,
                        raw={"moq_detected": moq, "supplier_type": normalizer.detect_supplier_type(text), "backend": backend},
                    ))
                if len(results) >= max_results:
                    return results
        return results

    async def search(self, request: SearchRequest, client) -> ConnectorOutcome:
        from ..query_builder import build_wholesale_queries

        queries = build_wholesale_queries(request)
        results = await asyncio.to_thread(self._run_sync, queries, 15)
        return ConnectorOutcome(results=results[:15])
