from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import get_current_user, require_admin
from app.models.user_model import UserModel
from app.schemas.auth_schema import UserProfile, ApiResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=ApiResponse[UserProfile],
    summary="Alias for /auth/me — current user profile",
)
async def get_me(
    current_user: UserModel = Depends(get_current_user),
) -> ApiResponse[UserProfile]:
    try:
        data = AuthService._profile(current_user)

        return ApiResponse.ok(
            data,
            message="User profile retrieved successfully",
        )

    except ValueError as e:
        return ApiResponse.fail(
            message="Invalid user profile data",
            errors=[str(e)],
        )


@router.get(
    "/{user_id}",
    response_model=ApiResponse[UserProfile],
    summary="Get any user by ID (admin only)",
    dependencies=[Depends(require_admin)],
)
async def get_user(
    user_id: int,
    current_user: UserModel = Depends(get_current_user),
) -> ApiResponse[UserProfile]:
    try:
        if current_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return ApiResponse.ok(
            AuthService._profile(current_user),
            message="User profile retrieved successfully",
        )

    except HTTPException:
        raise

    except ValueError as e:
        return ApiResponse.fail(
            message="Invalid user profile data",
            errors=[str(e)],
        )