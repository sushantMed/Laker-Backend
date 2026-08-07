from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis_client import Redis, get_redis
from app.core.config import settings
from app.core.mailer import Mailer
from app.database.session import get_db
from app.dependencies.mailer import get_mailer
from app.schemas.auth_schema import (
    LoginChallengeResponse,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    ResendOtpRequest,
    UserProfile,
    VerifyOtpRequest,
)
from app.schemas.common_schema import ApiResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])
bearer = HTTPBearer()
# Auth endpoints handle the missing-token case themselves so they can return a
# 401 instead of the default 403.
_optional_bearer = HTTPBearer(auto_error=False)


def get_bearer_token(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_optional_bearer)
    ],
) -> str:
    """Extract the bearer token, returning 401 when it is missing."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing.",
        )
    return credentials.credentials


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
    mailer: Annotated[Mailer, Depends(get_mailer)],
) -> ApiResponse[LoginResponse | LoginChallengeResponse]:
    data = await AuthService(
        session, redis, otp_secret=settings.otp_secret, mailer=mailer
    ).login(body)

    if isinstance(data, LoginChallengeResponse):
        message = "OTP sent successfully to your email"
    else:
        message = "Logged in successfully"

    return ApiResponse.ok(data, message=message)


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Revoke current access + refresh tokens",
)
async def logout(
    token: Annotated[str, Depends(get_bearer_token)],
    session: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> ApiResponse[None]:
    await AuthService(session, redis).logout(token)
    return ApiResponse.ok(None, message="Logout successful.")


@router.post(
    "/refresh",
    summary="Exchange a refresh token for a new token pair",
)
async def refresh(
    body: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> ApiResponse[RefreshResponse]:
    data = await AuthService(session, redis).refresh(body)
    return ApiResponse.ok(data, message="Token refreshed successfully.")


@router.get(
    "/me",
    summary="Return the profile of the authenticated user",
)
async def me(
    token: Annotated[str, Depends(get_bearer_token)],
    session: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> ApiResponse[UserProfile]:
    data = await AuthService(session, redis).me(token)
    return ApiResponse.ok(data, message="User profile retrieved successfully")


@router.post(
    "/verify-otp",
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ApiResponse[None], "description": "Invalid or expired OTP"},
        403: {"model": ApiResponse[None], "description": "Account inactive"},
        429: {"model": ApiResponse[None], "description": "Too many attempts"},
        500: {"model": ApiResponse[None], "description": "Internal server error"},
    },
    summary="Verify OTP and return access + refresh tokens",
)
async def verify_otp(
    body: VerifyOtpRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> ApiResponse[LoginResponse]:
    data = await AuthService(session, redis).verify_otp(body)
    return ApiResponse.ok(data, message="OTP verified successfully. You are logged in.")


@router.post(
    "/resend-otp",
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ApiResponse[None], "description": "Invalid or expired session"},
        403: {"model": ApiResponse[None], "description": "Account inactive"},
        429: {"model": ApiResponse[None], "description": "Resend rate limited"},
        500: {"model": ApiResponse[None], "description": "Internal server error"},
    },
    summary="Resend OTP to user email",
)
async def resend_otp(
    body: ResendOtpRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    mailer: Annotated[Mailer, Depends(get_mailer)],
) -> ApiResponse[LoginChallengeResponse]:
    data = await AuthService(session, redis, mailer=mailer).resend_otp(
        body.loginSessionId
    )
    return ApiResponse.ok(data, message="OTP resent successfully")
