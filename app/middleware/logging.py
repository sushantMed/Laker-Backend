"""
Middleware: Request / Response Logging
---------------------------------------
Logs every inbound request and its completed response including
latency (ms).  Sensitive headers (Authorization, Cookie) are redacted.
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.middleware.correlation_id import get_correlation_id

logger = logging.getLogger("laker.access")

_REDACTED_HEADERS = frozenset({"authorization", "cookie", "set-cookie"})


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        cid = get_correlation_id()

        logger.info(
            "→ %s %s  cid=%s  ip=%s",
            request.method,
            request.url.path,
            cid,
            _client_ip(request),
        )

        try:
            response: Response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1_000
            logger.exception("!! %s %s  cid=%s  error  %.1fms", request.method, request.url.path, cid, elapsed_ms)
            raise

        elapsed_ms = (time.perf_counter() - start) * 1_000
        level = logging.WARNING if response.status_code >= 400 else logging.INFO
        logger.log(
            level,
            "← %s %s  status=%d  cid=%s  %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            cid,
            elapsed_ms,
        )
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.1f}"
        return response


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
