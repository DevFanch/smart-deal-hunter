"""API Smart Deal Hunter — FastAPI.

Points d'entrée :
- POST /api/search        : recherche multi-sources (offres vérifiées + pistes)
- GET  /api/meta          : catégories, pays, devises, limites de saisie
- GET  /api/geo/defaults  : pays de destination par défaut (approximation IP)
- GET  /health            : supervision
"""
from __future__ import annotations

import logging

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .geo import guess_country
from .search.models import SearchRequest, SearchResponse
from .search.orchestrator import Orchestrator
from .security.input_sanitizer import QueryRejected, sanitize_query
from .security.rate_limit import RateLimiter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("sdh.api")

app = FastAPI(title=settings.api_title, version="0.1.0", docs_url="/api/docs", redoc_url=None)
rate_limiter = RateLimiter(settings.rate_limit_requests, settings.rate_limit_window_s)

# CORS : strict par défaut. Chrome envoie l'origine chrome-extension://<id>.
if settings.cors_allow_all_dev:
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
elif settings.cors_origins:
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                       allow_methods=["POST", "GET"], allow_headers=["Content-Type"])

app.middleware("http")(rate_limiter.middleware)

orchestrator = Orchestrator()

CATEGORIES = [
    "Automobile", "Chaussures", "Vêtements", "Informatique", "Téléphonie",
    "Électronique", "Maison", "Mobilier", "Sport", "Accessoires", "Autres",
]
COUNTRIES = ["FR", "DE", "ES", "IT", "BE", "NL", "PT", "AT", "IE", "PL", "GB", "US", "CA", "CH", "CN", "JP"]
CURRENCIES = ["EUR", "USD", "GBP", "CHF", "CAD"]
QUANTITIES = [1, 2, 5, 10, 12, 20, 24, 50, 100, 200, 500, 1000]


@app.exception_handler(QueryRejected)
async def query_rejected_handler(request: Request, exc: QueryRejected):
    """Rejet d'entrée malveillante : raison générique, sans écho du contenu."""
    return JSONResponse(status_code=422, content={"error": "invalid_query", "message": exc.reason})


@app.get("/health")
async def health():
    return {"status": "ok", "service": "smart-deal-hunter", "version": "0.1.0"}


@app.get("/api/meta")
async def meta():
    return {
        "categories": CATEGORIES,
        "countries": COUNTRIES,
        "currencies": CURRENCIES,
        "quantities": QUANTITIES,
        "max_query_length": settings.max_query_length,
        "deep_search_available": settings.deep_search_enabled,
        "monthly_budget_eur": settings.monthly_budget_eur,
    }


@app.get("/api/geo/defaults")
async def geo_defaults(request: Request):
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else None)
    async with httpx.AsyncClient() as client:
        country = await guess_country(ip, client)
    return {"destination_country": country, "source": "ip_approximation"}


@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest, raw_request: Request):
    # Validation stricte côté backend (l'extension valide aussi côté client)
    sanitize_query(request.query, max_length=settings.max_query_length)
    if request.postal_code and not request.postal_code.replace(" ", "").isalnum():
        return JSONResponse(status_code=422, content={"error": "invalid_query", "message": "code postal invalide"})
    if request.quantity is not None and (request.quantity < 1 or request.quantity > 1_000_000):
        return JSONResponse(status_code=422, content={"error": "invalid_query", "message": "quantité invalide"})
    async with httpx.AsyncClient(timeout=settings.search_timeout_s) as client:
        response = await orchestrator.run(request, client)
    return response
