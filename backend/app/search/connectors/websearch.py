"""Connecteur de recherche Web gratuit (moteurs publics via la librairie ddgs).

- Aucune clé API, aucun coût : niveau 1 (recherche standard).
- Accès non officiel : peut être temporairement limité ; les erreurs sont
  isolées et signalées dans les diagnostics, sans faire échouer la recherche.
- Les prix aperçus dans les extraits sont marqués `potentially_stale`.
"""
from __future__ import annotations

import asyncio
import logging

from ddgs import DDGS

from ..models import ConnectorResult, SearchRequest
from .base import BaseConnector, ConnectorOutcome

logger = logging.getLogger("sdh.connectors.websearch")

BACKENDS = ("bing", "duckduckgo", "yahoo")


class WebSearchConnector(BaseConnector):
    name = "websearch"
    enabled = True

    def __init__(self, max_results: int = 10) -> None:
        self.max_results = max_results

    def _run_sync(self, queries: list[str]) -> list[ConnectorResult]:
        results: list[ConnectorResult] = []
        errors: list[str] = []
        for backend in BACKENDS:
            if len(results) >= self.max_results:
                break
            for query in queries:
                try:
                    hits = DDGS().text(query, max_results=max(3, self.max_results // 2), backend=backend)
                except Exception as exc:  # limitation temporaire ou indisponibilité
                    errors.append(f"{backend}: {str(exc)[:80]}")
                    continue
                for hit in hits:
                    url = (hit.get("href") or "").strip()
                    if not url.startswith(("http://", "https://")):
                        continue
                    results.append(ConnectorResult(
                        url=url,
                        title=(hit.get("title") or "")[:300],
                        snippet=(hit.get("body") or "")[:500],
                        connector=self.name,
                        is_product_page_guess=True,
                        raw={"backend": backend, "query": query},
                    ))
                if len(results) >= self.max_results:
                    break
        if errors and not results:
            raise RuntimeError("; ".join(errors[:3]))
        if errors:
            logger.info("websearch erreurs partielles: %s", "; ".join(errors[:3]))
        return results

    async def search(self, request: SearchRequest, client) -> ConnectorOutcome:
        from ..query_builder import build_queries

        queries = build_queries(request)
        results = await asyncio.to_thread(self._run_sync, queries)
        return ConnectorOutcome(results=results[: self.max_results])
