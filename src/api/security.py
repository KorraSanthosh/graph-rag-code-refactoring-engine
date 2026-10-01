import hmac
import os
import threading
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Endpoints that call the LLM (and cost money) get rate limited.
EXPENSIVE_PATHS = ("/api/v1/refactor",)


class GuardMiddleware(BaseHTTPMiddleware):
    """
    Optional protection for a publicly deployed API:
      - ACCESS_KEY: if set, POST requests under /api/v1 must send `X-Access-Key`.
      - RATE_LIMIT_PER_MIN: max refactor calls per client IP per minute (0 disables).
    """

    def __init__(self, app, access_key: str | None = None, rate_limit: int | None = None):
        super().__init__(app)
        self.access_key = access_key if access_key is not None else os.getenv("ACCESS_KEY", "")
        self.rate_limit = (
            rate_limit if rate_limit is not None else int(os.getenv("RATE_LIMIT_PER_MIN", "10"))
        )
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if request.method == "POST" and path.startswith("/api/v1"):
            if self.access_key and not hmac.compare_digest(
                request.headers.get("x-access-key", ""), self.access_key
            ):
                return JSONResponse({"detail": "Invalid or missing access key."}, status_code=401)
            if self.rate_limit > 0 and path.startswith(EXPENSIVE_PATHS):
                if not self._allow(self._client_ip(request)):
                    return JSONResponse(
                        {"detail": "Rate limit exceeded. Try again in a minute."},
                        status_code=429,
                        headers={"Retry-After": "60"},
                    )
        return await call_next(request)

    @staticmethod
    def _client_ip(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _allow(self, ip: str) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[ip]
            while hits and now - hits[0] > 60:
                hits.popleft()
            if len(hits) >= self.rate_limit:
                return False
            hits.append(now)
            return True
