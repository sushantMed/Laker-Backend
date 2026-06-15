"""
Observability: Monitoring endpoint
------------------------------------
Exposes an internal /internal/metrics snapshot (admin-only in production).
"""

from fastapi import APIRouter

from app.observability.metrics import registry

monitor_router = APIRouter(prefix="/internal", tags=["Internal"])


@monitor_router.get("/metrics", include_in_schema=False)
async def metrics_snapshot() -> dict:
    return registry.snapshot()
