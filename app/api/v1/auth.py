from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis_client import Redis, get_redis
from app.core.config import settings
from app.core.mailer import Mailer
from app.database.session import get_db
from app.dependencies.mailer import get_mailer
from app.schemas.auth_schema import (
    ApiResponse,
    LoginChallengeResponse,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    ResendOtpRequest,
    UserProfile,
    VerifyOtpRequest,
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
    mailer: Annotated[Mailer, Depends(get_mailer)],
) -> ApiResponse[LoginResponse | LoginChallengeResponse]:
    data = await AuthService(
        session, redis, otp_secret=settings.otp_secret, mailer=mailer
    ).login(body)
    return ApiResponse.ok(data, message="OTP send succssfully to your email")


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
        return ApiResponse.fail(
            message="Failed to retrieve user profile", errors=[str(e)]
        )


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
    try:
        data = await AuthService(session, redis).verify_otp(body)
        return ApiResponse.ok(
            data, message="OTP verified successfully. You are logged in."
        )
    except Exception as e:
        return ApiResponse.fail(message="OTP verification failed", errors=[str(e)])


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
) -> ApiResponse[LoginChallengeResponse]:
    try:
        data = await AuthService(session, redis).resend_otp(body.loginSessionId)
        return ApiResponse.ok(data, message="OTP resent successfully")
    except Exception as e:
        return ApiResponse.fail(message="OTP resend failed", errors=[str(e)])
