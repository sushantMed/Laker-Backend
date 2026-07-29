from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis_client import Redis, get_redis
from app.database.session import get_db
from app.models.user_model import UserModel
from app.services.auth_service import AuthService

bearer = HTTPBearer()


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
) -> UserModel:
    """Resolve the bearer token to a live UserModel. Raises 401 on failure."""
    return await AuthService(session, redis).current_user(credentials.credentials)


# Roles are gone — every check is a grant check now. Use
# ``app.core.permissions.require(...)`` / ``RequireUser(...)``; admin-only
# endpoints gate on the "user admin" screen (Perm.USERADMIN_VIEW).
