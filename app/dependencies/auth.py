from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.user_model import UserModel
from app.services.auth_service import AuthService

bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    session: AsyncSession = Depends(get_db),
) -> UserModel:
    """Resolve the bearer token to a live UserModel. Raises 401 on failure."""
    return await AuthService(session).current_user(credentials.credentials)


def require_roles(*roles: str):
    """Factory — returns a dependency that enforces one of the given roles."""

    async def _check(user: UserModel = Depends(get_current_user)) -> UserModel:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _check


# Convenience shortcuts
require_admin      = require_roles("admin", "superadmin")
require_superadmin = require_roles("superadmin")
