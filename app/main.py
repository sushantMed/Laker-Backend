"""
Laker API  –  main.py
======================

Middleware stack (outermost → innermost, i.e. first added = outermost):

  Request
    │
    ▼
  SecurityHeaders      ← wraps everything; adds hardened response headers
    │
  RateLimit            ← drops excess requests before any real work
    │
  CorrelationId        ← assigns / propagates X-Correlation-ID
    │
  RequestContext       ← attaches path/method/IP to a ContextVar
    │
  Logging              ← logs request in / response out with latency
    ▼
  Router → Business Logic

Note: Starlette applies middleware in *reverse registration order*
(last added is outermost at the ASGI level), so we add them bottom-up.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.exceptions import AppException
from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import AppError, app_error_handler, generic_error_handler
from app.core.logging import setup_logging
from app.database.base import Base
from app.database.session import engine
from app.middleware.correlation_id import CorrelationIdMiddleware
from app.middleware.logging import LoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_context import RequestContextMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.observability.monitoring import monitor_router
from app.scripts.seed_users import seed_users
from app.schemas.auth_schema import ApiResponse
from app.scripts.seed_members import seed_members
from app.cache.redis_client import close_redis


# ── Import all models so SQLAlchemy can create tables ─────────────────────────
import app.models.user_model   # noqa: F401
import app.models.auth_model   # noqa: F401
import app.models.plan_model   # noqa: F401
import app.models.member_model # noqa: F401     
import app.models.member_address_model # noqa: F401


# ── Lifecycle ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_users()
    await seed_members()    
    yield
    await close_redis()
    await engine.dispose()




# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="Laker API",
        version=settings.app_version,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── Exception handlers ────────────────────────────────────────────────────
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_error_handler)
    
    # ── Custom middleware stack ───────────────────────────────────────────────
    # Added bottom-up: last registered = outermost at ASGI level.
    #
    # Desired call order (outermost first):
    #   CORSMiddleware → CorrelationId → RateLimit → RequestContext → Logging → SecurityHeaders
    #
    # So we register in reverse:

    app.add_middleware(SecurityHeadersMiddleware)   # innermost → applied last on response
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if not settings.is_production else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(api_router)
    app.include_router(monitor_router)



    return app


def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse.fail(message=exc.message).model_dump()
    )

def http_exception_handler(
    request: Request,
    exc: HTTPException,
):
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse.fail(
            message=str(exc.detail)
        ).model_dump()
    )

app = create_app()
