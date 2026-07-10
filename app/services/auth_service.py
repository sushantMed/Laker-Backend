import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import REFRESH_TOKEN_REMEMBER_ME_DAYS
from app.core.exceptions import (
    InvalidCredentialsError,
    TooManyAttemptsError,
    UserInactiveError,
    UserNotFoundError,
)
from app.core.security import (
    create_access_token,
    decode_access_token,
    opaque_token,
    token_expires_at,
    token_hash,
    verify_password,
)
from app.models.auth_model import RefreshTokenModel
from app.models.user_model import UserModel
from app.repositories.auth_repository import AuthRepository
from app.schemas.auth_schema import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    UserProfile,
)
from app.services.sshost_client import SSHostError, authenticate_user

logger = logging.getLogger("auth_service")


class AuthService:
    credentials_invalid: str = "Invalid credentials"
    refresh_token_invalid: str = "Invalid refresh token"
    refresh_token_expired: str = "Refresh token expired"
    unauthorized: str = "Unauthorized"

    MAX_ATTEMPTS = 5
    WINDOW_SECONDS = 15 * 60  # 15 minutes

    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self.repo = AuthRepository(session)
        self.redis = redis
        self.session = session

    async def login(self, request: LoginRequest) -> LoginResponse:
        if await self._is_rate_limited(request.email):
            raise TooManyAttemptsError()

        user = await self.repo.get_user_by_email(request.email)
        if not user:
            raise UserNotFoundError()

        if user.status != "ACTIVE":
            raise UserInactiveError()

        if not await self._verify_credentials(request.email, request.password, user):
            await self._register_failed_attempt(request.email)
            raise InvalidCredentialsError()

        await self._clear_attempts(request.email)

        access_token, _, expires_in = create_access_token(
            subject=str(user.id),
            email=user.email,
            role=user.role,
        )
        refresh_token = await self._create_refresh_token(user)

        return LoginResponse(
            accessToken=access_token,
            refreshToken=refresh_token.token,
            expiresIn=expires_in,
        )

    async def _verify_credentials(
        self, email: str, password: str, user: UserModel
    ) -> bool:
        try:
            sshost_ok = await authenticate_user(email, password)
            print(f"SSHost authentication result for {email}: {sshost_ok}")
        except SSHostError as exc:
            logger.warning(
                "SSHost unavailable (%s), falling back to local DB verification for %s",
                exc,
                email,
            )
            return verify_password(password, user.hashed_password)

        return sshost_ok is not False

    async def _is_rate_limited(self, email: str) -> bool:
        key = f"login_attempts:{email.lower()}"
        attempts = await self.redis.get(key)
        return attempts is not None and int(attempts) >= self.MAX_ATTEMPTS

    async def _register_failed_attempt(self, email: str) -> None:
        key = f"login_attempts:{email.lower()}"
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, self.WINDOW_SECONDS, nx=True)
            await pipe.execute()

    async def _clear_attempts(self, email: str) -> None:
        await self.redis.delete(f"login_attempts:{email.lower()}")

    async def logout(self, access_token: str) -> None:
        claims = decode_access_token(access_token, verify_exp=False)
        await self.repo.revoke_user_refresh_tokens(UUID(claims["sub"]))
        await self.repo.revoke_access_token(
            token_hash(access_token), token_expires_at(access_token)
        )

    async def refresh(self, request: RefreshRequest) -> RefreshResponse:
        current = await self.repo.get_refresh_token(request.refreshToken)
        if not current:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=self.refresh_token_invalid,
            )

        now = datetime.now(UTC)
        expires_at = current.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        if current.revoked or current.consumed:
            # Token reuse detected — revoke entire family (rotation protection)
            await self.repo.revoke_refresh_family(current.family_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=self.refresh_token_invalid,
            )

        if expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=self.refresh_token_expired,
            )

        user = await self.repo.get_user_by_id(current.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=self.refresh_token_invalid,
            )

        current.consumed = True
        new_refresh = await self._create_refresh_token(
            user, family_id=current.family_id
        )
        access_token, _, expires_in = create_access_token(
            subject=str(user.id),
            email=user.email,
            role=user.role,
        )
        return RefreshResponse(
            accessToken=access_token,
            refreshToken=new_refresh.token,
            expiresIn=expires_in,
        )

    async def me(self, access_token: str) -> UserProfile:
        user = await self.current_user(access_token)
        return self._profile(user)

    async def current_user(self, access_token: str) -> UserModel:
        claims = decode_access_token(access_token)
        if await self.repo.is_access_token_revoked(token_hash(access_token)):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=self.unauthorized
            )
        try:
            user_id = UUID(claims["sub"])
        except (KeyError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=self.unauthorized
            ) from None
        user = await self.repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=self.unauthorized
            )
        return user

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _create_refresh_token(
        self,
        user: UserModel,
        # remember_me: bool,
        family_id: str | None = None,
    ) -> RefreshTokenModel:
        days = REFRESH_TOKEN_REMEMBER_ME_DAYS
        token = RefreshTokenModel(
            token=opaque_token(),
            family_id=family_id or str(uuid4()),
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(days=days),
        )
        return await self.repo.save_refresh_token(token)

    @staticmethod
    def _profile(user: UserModel) -> UserProfile:
        first = user.first_name[:1] if user.first_name else ""
        last = user.last_name[:1] if user.last_name else ""
        return UserProfile(
            userId=str(user.id),
            firstName=user.first_name,
            lastName=user.last_name,
            email=user.email,
            role=user.role,
            initials=f"{first}{last}".upper(),
            status=user.status,
            permissions=AuthService._permissions(user.role),
        )

    @staticmethod
    def _permissions(role: str) -> list[str]:
        _map = {
            "superadmin": [
                "users:read",
                "users:write",
                "members:read",
                "claims:read",
                "auth:read",
            ],
            "admin": ["users:read", "members:read", "claims:read", "auth:read"],
            "readonly": ["members:read", "claims:read"],
            "user": ["members:read", "claims:read"],
        }
        return _map.get(role, ["members:read", "claims:read"])
