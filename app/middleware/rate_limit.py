"""
Middleware: Rate Limiting  (token-bucket, in-process)
------------------------------------------------------
Uses a simple token-bucket per client IP.  Production deployments
should swap this for a Redis-backed implementation to work across
multiple worker processes.

Can be disabled via RATE_LIMIT_ENABLED=false in .env.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock

from fastapi import status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.core.config import settings


@dataclass
class _Bucket:
    tokens: float
    last_refill: float = field(default_factory=time.monotonic)
    lock: Lock = field(default_factory=Lock, compare=False, repr=False)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Token-bucket per IP.

    Config (via Settings):
        rate_limit_requests       – max burst / tokens per window
        rate_limit_window_seconds – refill window length in seconds
    """

    def __init__(self, app, **kwargs) -> None:
        super().__init__(app, **kwargs)
        self._buckets: dict[str, _Bucket] = defaultdict(
            lambda: _Bucket(tokens=settings.rate_limit_requests)
        )
        self._capacity = settings.rate_limit_requests
        self._rate = settings.rate_limit_requests / settings.rate_limit_window_seconds  # tokens/sec

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.rate_limit_enabled:
            return await call_next(request)

        ip = self._client_ip(request)
        if not self._consume(ip):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content="Too many requests — please slow down",
                headers={"Retry-After": str(settings.rate_limit_window_seconds)},
            )

        response = await call_next(request)
        return response

    def _consume(self, ip: str) -> bool:
        bucket = self._buckets[ip]
        with bucket.lock:
            now = time.monotonic()
            elapsed = now - bucket.last_refill
            bucket.tokens = min(self._capacity, bucket.tokens + elapsed * self._rate)
            bucket.last_refill = now
            if bucket.tokens >= 1:
                bucket.tokens -= 1
                return True
            return False

    @staticmethod
    def _client_ip(request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
