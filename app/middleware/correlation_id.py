"""
Middleware: Correlation ID
--------------------------
Reads X-Correlation-ID from the incoming request (or generates one)
and propagates it on the response.  Also stores it in a ContextVar
so any code deeper in the stack can retrieve it via `get_correlation_id()`.
"""

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.constants import CORRELATION_ID_HEADER

_correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    return _correlation_id_ctx.get()


# we can use this in main
class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        cid = request.headers.get(CORRELATION_ID_HEADER) or str(uuid.uuid4())
        token = _correlation_id_ctx.set(cid)
        try:
            response: Response = await call_next(request)
        finally:
            _correlation_id_ctx.reset(token)

        response.headers[CORRELATION_ID_HEADER] = cid
        return response
