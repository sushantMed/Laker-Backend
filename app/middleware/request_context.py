"""
Middleware: Request Context
---------------------------
Stores a request-scoped dict in a ContextVar so any downstream code
can attach arbitrary metadata (user_id, tenant, etc.) without threading
it through every function signature.
"""

from contextvars import ContextVar
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_request_ctx: ContextVar[dict[str, Any]] = ContextVar("request_context", default={})


def get_request_context() -> dict[str, Any]:
    return _request_ctx.get()


def set_context_value(key: str, value: Any) -> None:
    ctx = _request_ctx.get()
    _request_ctx.set({**ctx, key: value})


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        token = _request_ctx.set(
            {
                "path": request.url.path,
                "method": request.method,
                "client_ip": _client_ip(request),
            }
        )
        try:
            return await call_next(request)
        finally:
            _request_ctx.reset(token)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
