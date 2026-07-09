from fastapi import APIRouter, Depends
from typing import Annotated
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.session import get_db
from app.cache.redis_client import check_redis_health

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", summary="Liveness probe")
async def liveness() -> dict:
    return {"status": "ok", "version": settings.app_version}


@router.get("/ready", summary="Readiness probe — checks DB and cache connectivity")
async def readiness(session: Annotated[AsyncSession, Depends(get_db)]) -> dict:
    try:
        await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:
        db_status = f"error: {exc}"

    redis_status = "ok" if await check_redis_health() else "error: unreachable"

    overall = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"

    return {
        "status": overall,
        "version": settings.app_version,
        "checks": {"database": db_status, "redis": redis_status},
    }
