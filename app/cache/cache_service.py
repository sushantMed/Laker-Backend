"""
Cache service: thin wrapper over Redis with graceful degradation.

If Redis is unavailable, all operations fail silently (log + return None/no-op)
so the app continues serving from DB — cache is an optimization, not a dependency.
"""

import json
import logging
from typing import TypeVar

from pydantic import BaseModel

from app.cache.redis_client import redis_client
from app.core.config import settings

logger = logging.getLogger("laker.cache")

T = TypeVar("T", bound=BaseModel)


class CacheService:
    def __init__(self, namespace: str):
        """
        namespace: logical grouping, e.g. 'member', 'plan' — becomes key prefix.
        """
        self._namespace = namespace

    def _key(self, identifier: str) -> str:
        return f"{settings.app_env}:{self._namespace}:{identifier}"

    async def get(self, identifier: str, schema: type[T]) -> T | None:
        if not settings.cache_enabled:
            return None
        try:
            raw = await redis_client.get(self._key(identifier))
            if raw is None:
                return None
            return schema.model_validate(json.loads(raw))
        except Exception:
            logger.warning("Cache GET failed for %s", self._key(identifier), exc_info=True)
            return None  # degrade gracefully — treat as cache miss

    async def set(self, identifier: str, value: BaseModel, ttl: int | None = None) -> None:
        if not settings.cache_enabled:
            return
        try:
            await redis_client.set(
                self._key(identifier),
                value.model_dump_json(),
                ex=ttl or settings.cache_default_ttl_seconds,
            )
        except Exception:
            logger.warning("Cache SET failed for %s", self._key(identifier), exc_info=True)
            # don't raise — caching failure shouldn't break the request

    async def delete(self, identifier: str) -> None:
        if not settings.cache_enabled:
            return
        try:
            await redis_client.delete(self._key(identifier))
        except Exception:
            logger.warning("Cache DELETE failed for %s", self._key(identifier), exc_info=True)

    async def delete_pattern(self, pattern: str) -> None:
        """For bulk invalidation, e.g. all search results for a member."""
        if not settings.cache_enabled:
            return
        try:
            keys = []
            async for key in redis_client.scan_iter(match=self._key(pattern)):
                keys.append(key)
            if keys:
                await redis_client.delete(*keys)
        except Exception:
            logger.warning("Cache pattern delete failed for %s", pattern, exc_info=True)
