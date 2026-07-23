from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.core.rbac import Perm  # re-exported for convenience
from app.dependencies.auth import get_current_user
from app.models.user_model import UserModel

__all__ = ["Perm", "RequireUser", "require"]


def require(*perms: str):
    """Dependency factory — passes only if the user holds every listed permission."""

    async def _check(
        current_user: Annotated[UserModel, Depends(get_current_user)],
    ) -> UserModel:
        if current_user.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Account is not active"
            )
        missing = set(perms) - current_user.permission_set
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {', '.join(sorted(missing))}",
            )
        return current_user

    return _check


def RequireUser(*perms: str):
    """Annotated dependency: ``current_user: RequireUser(Perm.DRUG_VIEW)``."""
    return Annotated[UserModel, Depends(require(*perms))]
