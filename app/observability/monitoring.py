"""
Observability: Monitoring endpoint
------------------------------------
Exposes an internal /internal/metrics snapshot (admin-only in production).
"""

from fastapi import APIRouter

from app.observability.metrics import registry

from app.cache.redis_client import check_redis_health

monitor_router = APIRouter(prefix="/internal", tags=["Internal"])


@monitor_router.get("/metrics", include_in_schema=False)
async def metrics_snapshot() -> dict:
    return registry.snapshot()

@monitor_router.get("/redis-health", include_in_schema=True)
async def redis_health() -> dict:

    is_healthy = await check_redis_health()
    return {"redis_healthy": is_healthy}
