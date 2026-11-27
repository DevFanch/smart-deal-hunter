"""Rate limiting simple en mémoire (fenêtre glissante, par IP).

Volontairement sans dépendance externe : suffit pour une bêta privée mono-instance.
"""
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse


class RateLimiter:
    def __init__(self, max_requests: int, window_s: int) -> None:
        self.max_requests = max_requests
        self.window_s = window_s
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _client_key(self, request: Request) -> str:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def check(self, request: Request) -> bool:
        key = self._client_key(request)
        now = time.monotonic()
        dq = self._hits[key]
        while dq and now - dq[0] > self.window_s:
            dq.popleft()
        if len(dq) >= self.max_requests:
            return False
        dq.append(now)
        return True

    def reset(self) -> None:
        self._hits.clear()

    async def middleware(self, request: Request, call_next):
        if request.url.path.startswith("/api/"):
            if not self.check(request):
                return JSONResponse(
                    status_code=429,
                    content={"error": "rate_limited", "message": "Trop de requêtes, réessayez plus tard."},
                )
        return await call_next(request)
