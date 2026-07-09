from typing import Annotated

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
    summary="Authenticate user and obtain tokens",
)
async def login(
    body: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[LoginResponse]:
    try:
        data = await AuthService(session).login(body)
        return ApiResponse.ok(data, message="Login successful")
    except Exception as e:
        return ApiResponse.fail(message="Login failed", errors=[str(e)])

@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke current access + refresh tokens",
)
async def logout(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    await AuthService(session).logout(credentials.credentials)


@router.post(
    "/refresh",
    summary="Exchange a refresh token for a new token pair",
)
async def refresh(
    body: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[RefreshResponse]:
    try:
        data = await AuthService(session).refresh(body)
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
) -> ApiResponse[UserProfile]:
    try:
        data = await AuthService(session).me(credentials.credentials)
        print("User profile retrieved successfully:", data)
        return ApiResponse.ok(data, message="User profile retrieved successfully")
    except Exception as e:
        return ApiResponse.fail(message="Failed to retrieve user profile", errors=[str(e)])
