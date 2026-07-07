from typing import Annotated

from app.cache.redis_client import get_redis, Redis
from fastapi import APIRouter, Depends, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession


from app.database.session import get_db
from app.schemas.auth_schema import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    UserProfile,
    ApiResponse
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])
bearer = HTTPBearer()


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ApiResponse[None], "description": "Invalid credentials"},
        403: {"model": ApiResponse[None], "description": "Account inactive"},
        404: {"model": ApiResponse[None], "description": "User not found"},
        422: {"model": ApiResponse[None], "description": "Validation error"},
        429: {"model": ApiResponse[None], "description": "Rate limited"},
        500: {"model": ApiResponse[None], "description": "Internal server error"},
    },
    summary="Authenticate user and return access + refresh tokens",
)
async def login(
    body: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> ApiResponse[LoginResponse]:
    data = await AuthService(session, redis).login(body)
    return ApiResponse.ok(data, message="Login successful")

@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke current access + refresh tokens",
)
async def logout(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
    session: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> None:
    await AuthService(session, redis).logout(credentials.credentials)


@router.post(
    "/refresh",
    summary="Exchange a refresh token for a new token pair",
)
async def refresh(
    body: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> ApiResponse[RefreshResponse]:
    try:
        data = await AuthService(session, redis).refresh(body)
        return ApiResponse.ok(data, message="Token refresh successful")
    except Exception as e:
        return ApiResponse.fail(message="Token refresh failed", errors=[str(e)])


@router.get(
    "/me",
    summary="Return the profile of the authenticated user",
)
async def me(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
    session: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> ApiResponse[UserProfile]:
    try:
        data = await AuthService(session, redis).me(credentials.credentials)
        print("User profile retrieved successfully:", data)
        return ApiResponse.ok(data, message="User profile retrieved successfully")
    except Exception as e:
        return ApiResponse.fail(message="Failed to retrieve user profile", errors=[str(e)])