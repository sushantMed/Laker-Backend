from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.session import get_db

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", summary="Liveness probe")
async def liveness() -> dict:
    return {"status": "ok", "version": settings.app_version}


@router.get("/ready", summary="Readiness probe — checks DB connectivity")
async def readiness(session: AsyncSession = Depends(get_db)) -> dict:
    try:
        await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:
        db_status = f"error: {exc}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "version": settings.app_version,
        "checks": {"database": db_status},
    }
