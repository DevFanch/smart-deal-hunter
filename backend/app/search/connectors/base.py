"""Interface commune des connecteurs.

Chaque connecteur :
- reçoit une requête normalisée ;
- interroge SA source ;
- retourne des résultats bruts (ConnectorResult) ;
- signale ses erreurs sans jamais faire échouer la recherche globale ;
- indique son niveau d'accessibilité via un rapport (ConnectorReport).
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import httpx

from ..models import ConnectorReport, ConnectorResult, SearchRequest


@dataclass
class ConnectorOutcome:
    results: list[ConnectorResult] = field(default_factory=list)
    report: ConnectorReport | None = None
    disabled_reason: str | None = None


class BaseConnector(ABC):
    name: str = "base"
    enabled: bool = True

    @abstractmethod
    async def search(self, request: SearchRequest, client: httpx.AsyncClient) -> ConnectorOutcome:
        ...

    def _report(self, results: list[ConnectorResult], start: float, error: str | None = None) -> ConnectorReport:
        status = "ok" if not error else "error"
        if not error and not results:
            status = "degraded"
        return ConnectorReport(
            name=self.name,
            status=status,
            results=len(results),
            error=error,
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    async def safe_search(self, request: SearchRequest, client: httpx.AsyncClient) -> ConnectorOutcome:
        """Exécute le connecteur et capture toute erreur : un connecteur défaillant
        ne fait jamais échouer l'ensemble de la recherche."""
        start = time.monotonic()
        if not self.enabled:
            return ConnectorOutcome(disabled_reason=f"connecteur {self.name} désactivé")
        try:
            outcome = await self.search(request, client)
            outcome.report = outcome.report or self._report(outcome.results, start)
            return outcome
        except Exception as exc:  # noqa: BLE001 - isolation volontaire
            report = self._report([], start, error=f"{type(exc).__name__}: {exc}"[:200])
            return ConnectorOutcome(results=[], report=report)
