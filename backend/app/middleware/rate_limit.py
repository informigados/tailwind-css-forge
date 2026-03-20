from __future__ import annotations

import math
import threading
import time
from collections import defaultdict, deque

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class LocalRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        max_requests: int,
        window_seconds: int,
        protected_methods: tuple[str, ...] = ("POST", "PUT", "DELETE"),
    ) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.protected_methods = protected_methods
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self._should_limit(request):
            return await call_next(request)

        key = self._build_key(request)
        now = time.monotonic()
        denied = False
        retry_after = 0

        with self._lock:
            entries = self._hits[key]
            self._prune(entries, now)
            if len(entries) >= self.max_requests:
                denied = True
                retry_after = self._retry_after_seconds(entries, now)
            else:
                entries.append(now)

        if denied:
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(retry_after)},
                content={
                    "detail": "Limite local de requisicoes atingido para operacoes mutaveis. Aguarde alguns segundos e tente novamente.",
                },
            )

        return await call_next(request)

    def _should_limit(self, request: Request) -> bool:
        if self.max_requests <= 0 or self.window_seconds <= 0:
            return False
        if request.method.upper() not in self.protected_methods:
            return False
        if not request.url.path.startswith("/api/"):
            return False
        return request.url.path not in {"/api/health", "/api/i18n"}

    def _build_key(self, request: Request) -> str:
        client_host = request.client.host if request.client else "local"
        return f"{client_host}:{request.method.upper()}:{request.url.path}"

    def _prune(self, entries: deque[float], now: float) -> None:
        cutoff = now - self.window_seconds
        while entries and entries[0] <= cutoff:
            entries.popleft()

    def _retry_after_seconds(self, entries: deque[float], now: float) -> int:
        if not entries:
            return 1
        return max(1, math.ceil((entries[0] + self.window_seconds) - now))
