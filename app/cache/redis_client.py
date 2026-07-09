import redis.asyncio as redis
from app.core.config import settings

# Connection pool — reused across requests, handles concurrency
redis_pool = redis.ConnectionPool(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    decode_responses=True,
    max_connections=50,
    socket_connect_timeout=2,
    socket_timeout=2,
)

redis_client = redis.Redis(connection_pool=redis_pool)


async def check_redis_health() -> bool:
    try:
        await redis_client.ping()
        return True
    except Exception:
        return False


async def close_redis() -> None:
    await redis_client.aclose()
