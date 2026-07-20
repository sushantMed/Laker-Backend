import hashlib
import hmac
import logging
import secrets
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import REFRESH_TOKEN_REMEMBER_ME_DAYS
from app.core.exceptions import (
    InvalidCredentialsError,
    InvalidOrExpiredOtpError,
    OtpResendRateLimitedError,
    TooManyAttemptsError,
    UserInactiveError,
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
    LoginChallengeResponse,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    UserProfile,
    VerifyOtpRequest,
)
from app.services.sshost_client import SSHostError, authenticate_user

logger = logging.getLogger("auth_service")

# ---------------------------------------------------------------------------
# OTP configuration
# ---------------------------------------------------------------------------

OTP_TTL_SECONDS = 300  # 5 minutes
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN_SECONDS = 60
OTP_LENGTH = 6

OTP_KEY_PREFIX = "otp:challenge:"
OTP_RESEND_COOLDOWN_PREFIX = "otp:cooldown:"


_DUMMY_OTP_HASH = hashlib.sha256(b"dummy").hexdigest()

# Known-bad secrets that must never be used in a real deployment
_INSECURE_OTP_SECRET_SENTINELS = {"default-secret", "changeme", "secret", ""}


@dataclass
class OtpChallenge:
    user_id: str
    email: str
    otp_hash: str
    attempts: int
    created_at: float


class OtpStore:
    """Thin wrapper around redis for OTP challenge storage."""

    def __init__(self, redis_client):
        self.redis = redis_client

    @staticmethod
    def _key(login_session_id: str) -> str:
        return f"{OTP_KEY_PREFIX}{login_session_id}"

    @staticmethod
    def _cooldown_key(user_id: str) -> str:
        return f"{OTP_RESEND_COOLDOWN_PREFIX}{user_id}"

    async def is_resend_rate_limited(self, user_id: str) -> bool:
        return await self.redis.exists(self._cooldown_key(user_id)) == 1

    async def set_resend_cooldown(self, user_id: str) -> None:
        await self.redis.set(
            self._cooldown_key(user_id), "1", ex=OTP_RESEND_COOLDOWN_SECONDS
        )

    async def create(
        self, login_session_id: str, user_id: str, email: str, otp_hash: str
    ) -> None:
        payload = {
            "user_id": user_id,
            "email": email,
            "otp_hash": otp_hash,
            "attempts": "0",
            "created_at": str(time.time()),
        }
        key = self._key(login_session_id)
        # SCALABILITY: hset + expire is two round trips; pipeline them so
        # OTP creation stays a single network round trip under load.
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.hset(key, mapping=payload)
            pipe.expire(key, OTP_TTL_SECONDS)
            await pipe.execute()

    @staticmethod
    def _decode_field(data: dict, field: str) -> str | None:
        """Handle both decode_responses=True and raw-bytes redis clients."""
        if field in data:
            v = data[field]
        elif field.encode() in data:
            v = data[field.encode()]
        else:
            return None
        return v.decode() if isinstance(v, bytes) else v

    async def get(self, login_session_id: str) -> OtpChallenge | None:
        key = self._key(login_session_id)
        data = await self.redis.hgetall(key)
        if not data:
            return None

        user_id = self._decode_field(data, "user_id")
        email = self._decode_field(data, "email")
        otp_hash = self._decode_field(data, "otp_hash")
        attempts = self._decode_field(data, "attempts")
        created_at = self._decode_field(data, "created_at")

        if None in (user_id, email, otp_hash, attempts, created_at):
            # Corrupt/partial record — treat as absent rather than 500ing.
            logger.warning(
                "Corrupt OTP challenge record for session %s", login_session_id
            )
            return None

        return OtpChallenge(
            user_id=user_id,
            email=email,
            otp_hash=otp_hash,
            attempts=int(attempts),
            created_at=float(created_at),
        )

    async def increment_attempts(self, login_session_id: str) -> int:
        key = self._key(login_session_id)
        return await self.redis.hincrby(key, "attempts", 1)

    async def delete(self, login_session_id: str) -> None:
        await self.redis.delete(self._key(login_session_id))


# ---------------------------------------------------------------------------
# OTP helpers
# ---------------------------------------------------------------------------


def _generate_otp() -> str:
    """6-digit numeric OTP using a CSPRNG, zero-padded."""
    return f"{secrets.randbelow(10**OTP_LENGTH):0{OTP_LENGTH}d}"


def _hash_otp(otp: str, login_session_id: str, secret_key: str) -> str:
    """HMAC the OTP so it's never stored in plaintext."""
    msg = f"{login_session_id}:{otp}".encode()
    return hmac.new(secret_key.encode(), msg, hashlib.sha256).hexdigest()


def _is_valid_otp_format(otp: str) -> bool:
    return len(otp) == OTP_LENGTH and otp.isdigit()


class AuthService:
    credentials_invalid: str = "Invalid credentials"
    refresh_token_invalid: str = "Invalid refresh token"
    refresh_token_expired: str = "Refresh token expired"
    unauthorized: str = "Unauthorized"

    MAX_ATTEMPTS = 5
    WINDOW_SECONDS = 15 * 60  # 15 minutes

    IP_MAX_ATTEMPTS = 30
    IP_WINDOW_SECONDS = 15 * 60

    def __init__(
        self,
        session: AsyncSession,
        redis: Redis,
        mailer=None,
        otp_secret: str | None = None,
    ) -> None:
        effective_secret = otp_secret or getattr(settings, "otp_secret", None)
        if (
            not effective_secret
            or effective_secret.lower() in _INSECURE_OTP_SECRET_SENTINELS
        ):
            raise RuntimeError(
                "AuthService requires a real otp_secret (via settings.otp_secret "
                "or constructor arg); refusing to start with an insecure/missing value."
            )

        self.repo = AuthRepository(session)
        self.redis = redis
        self.session = session
        self.mailer = mailer
        self.otp_store = OtpStore(redis)
        self.otp_secret = effective_secret

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def login(
        self, request: LoginRequest, client_ip: str | None = None
    ) -> LoginResponse | LoginChallengeResponse:
        """
        Verify credentials and, depending on `settings.OTP_ENABLED`, either:
          - OTP_ENABLED = True  -> issue an OTP challenge (2FA is enforced;
            caller must then call `verify_otp` to receive tokens), or
          - OTP_ENABLED = False -> issue access/refresh tokens directly.
        """
        if await self._is_rate_limited(request.email, client_ip):
            raise TooManyAttemptsError()

        user = await self.repo.get_user_by_email(request.email)

        if user is None:
            await self._register_failed_attempt(request.email, client_ip)
            raise InvalidCredentialsError()

        if not await self._verify_credentials(request.email, request.password, user):
            await self._register_failed_attempt(request.email, client_ip)
            raise InvalidCredentialsError()

        if user.status != "ACTIVE":
            raise UserInactiveError()

        await self._clear_attempts(request.email, client_ip)

        if settings.otp_enabled:
            return await self._issue_otp_challenge(user)

        return await self._issue_tokens(user)

    async def verify_otp(self, request: VerifyOtpRequest) -> LoginResponse:
        """Verify OTP and return access/refresh tokens."""
        if not _is_valid_otp_format(request.otp):
            raise InvalidOrExpiredOtpError()

        challenge = await self.otp_store.get(request.loginSessionId)

        if not challenge:
            raise InvalidOrExpiredOtpError()

        if challenge.attempts >= OTP_MAX_ATTEMPTS:
            await self.otp_store.delete(request.loginSessionId)
            raise TooManyAttemptsError()

        candidate_hash = _hash_otp(request.otp, request.loginSessionId, self.otp_secret)

        if not hmac.compare_digest(candidate_hash, challenge.otp_hash):
            attempts = await self.otp_store.increment_attempts(request.loginSessionId)
            if attempts >= OTP_MAX_ATTEMPTS:
                await self.otp_store.delete(request.loginSessionId)
                raise TooManyAttemptsError()
            raise InvalidOrExpiredOtpError()

        # Success — consume the challenge immediately so it can't be replayed.
        await self.otp_store.delete(request.loginSessionId)

        user = await self.repo.get_user_by_id(UUID(challenge.user_id))
        if not user or user.status != "ACTIVE":
            raise UserInactiveError()

        logger.info("OTP verified, tokens issued for user_id=%s", user.id)
        return await self._issue_tokens(user)

    async def resend_otp(self, login_session_id: str) -> LoginChallengeResponse:
        """Resend OTP to user email."""
        challenge = await self.otp_store.get(login_session_id)
        if not challenge:
            raise InvalidOrExpiredOtpError()

        if await self.otp_store.is_resend_rate_limited(challenge.user_id):
            raise OtpResendRateLimitedError()

        user = await self.repo.get_user_by_id(UUID(challenge.user_id))
        if not user or user.status != "ACTIVE":
            raise UserInactiveError()

        await self.otp_store.delete(login_session_id)
        return await self._issue_otp_challenge(user)

    async def _issue_otp_challenge(self, user: UserModel) -> LoginChallengeResponse:
        """Generate an OTP, persist the challenge, and enforce delivery via email.

        Email delivery is treated as required: if we can't send the code,
        the challenge is torn down and a 503 is raised rather than
        leaving the user stuck waiting on an email that never arrives.
        """
        login_session_id = str(uuid.uuid4())
        otp = _generate_otp()
        otp_hash = _hash_otp(otp, login_session_id, self.otp_secret)

        await self.otp_store.create(
            login_session_id=login_session_id,
            user_id=str(user.id),
            email=user.email,
            otp_hash=otp_hash,
        )
        await self.otp_store.set_resend_cooldown(str(user.id))

        if not self.mailer:
            logger.error(
                "OTP_ENABLED is True but no mailer is configured; cannot send OTP for user_id=%s",
                user.id,
            )
            await self.otp_store.delete(login_session_id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to send verification code. Please try again later.",
            )

        print(f"Sending OTP email to {user.email} with code {otp}")
        try:
            print(
                f"DEBUG: OTP for user_id={user.id} is {otp} (expires in {OTP_TTL_SECONDS} seconds)"
            )
            await self.mailer.send_email(
                to=[user.email],
                subject="Your login verification code",
                html=f"Your verification code is <strong>{otp}</strong>. It expires in "
                f"{OTP_TTL_SECONDS // 60} minutes. Do not share this code.",
            )
        except Exception as e:
            logger.error("Failed to send OTP email for user_id=%s: %s", user.id, e)
            await self.otp_store.delete(login_session_id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to send verification code. Please try again later.",
            ) from e

        return LoginChallengeResponse(
            loginSessionId=login_session_id,
            otpRequired=True,
            expiresIn=OTP_TTL_SECONDS,
        )

    async def _issue_tokens(self, user: UserModel) -> LoginResponse:
        """Issue access + refresh tokens for an already-authenticated user."""
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
        except SSHostError as exc:
            logger.warning(
                "SSHost unavailable (%s), falling back to local DB verification for user_id=%s",
                exc,
                user.id,
            )
            return verify_password(password, user.hashed_password)

        return sshost_ok is True

    async def _is_rate_limited(self, email: str, client_ip: str | None) -> bool:
        email_key = f"login_attempts:email:{email.lower()}"
        attempts = await self.redis.get(email_key)
        if attempts is not None and int(attempts) >= self.MAX_ATTEMPTS:
            return True

        if client_ip:
            ip_key = f"login_attempts:ip:{client_ip}"
            ip_attempts = await self.redis.get(ip_key)
            if ip_attempts is not None and int(ip_attempts) >= self.IP_MAX_ATTEMPTS:
                return True

        return False

    async def _register_failed_attempt(self, email: str, client_ip: str | None) -> None:
        email_key = f"login_attempts:email:{email.lower()}"
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.incr(email_key)
            pipe.expire(email_key, self.WINDOW_SECONDS, nx=True)
            if client_ip:
                ip_key = f"login_attempts:ip:{client_ip}"
                pipe.incr(ip_key)
                pipe.expire(ip_key, self.IP_WINDOW_SECONDS, nx=True)
            await pipe.execute()

    async def _clear_attempts(self, email: str, client_ip: str | None) -> None:
        keys = [f"login_attempts:email:{email.lower()}"]
        if client_ip:
            keys.append(f"login_attempts:ip:{client_ip}")
        await self.redis.delete(*keys)

    async def logout(self, access_token: str) -> None:
        try:
            claims = decode_access_token(access_token, verify_exp=False)
            user_id = UUID(claims["sub"])
        except Exception:
            # FIX: don't let a malformed/tampered token throw a raw 500 —
            # logout is idempotent from the caller's point of view.
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=self.unauthorized
            ) from None

        await self.repo.revoke_user_refresh_tokens(user_id)
        await self.repo.revoke_access_token(
            token_hash(access_token), token_expires_at(access_token)
        )

    async def refresh(self, request: RefreshRequest) -> RefreshResponse:
        presented_hash = token_hash(request.refreshToken)

        # FIX: look up by hash, not plaintext — plaintext refresh tokens
        # at rest are a standing liability if the DB is ever exposed
        # (backups, replicas, read access via another vuln).
        current = await self.repo.get_refresh_token_by_hash(presented_hash)
        if not current:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=self.refresh_token_invalid,
            )

        now = datetime.now(UTC)
        expires_at = current.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        if expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=self.refresh_token_expired,
            )

        # FIX (race condition): atomically flip consumed=false -> true at
        # the DB layer. If this returns None, either the token was never
        # valid, or — more importantly — it was *already consumed*,
        # meaning this is a reuse of a rotated-out token: revoke the
        # whole family immediately.
        consumed = await self.repo.consume_refresh_token_atomic(presented_hash)
        if consumed is None:
            if current.family_id:
                await self.repo.revoke_refresh_family(current.family_id)
            logger.warning(
                "Refresh token reuse detected for family_id=%s", current.family_id
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=self.refresh_token_invalid,
            )

        user = await self.repo.get_user_by_id(consumed.user_id)
        if not user or user.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=self.refresh_token_invalid,
            )

        new_refresh_token = await self._create_refresh_token(
            user, family_id=consumed.family_id
        )
        access_token, _, expires_in = create_access_token(
            subject=str(user.id),
            email=user.email,
            role=user.role,
        )
        return RefreshResponse(
            accessToken=access_token,
            refreshToken=new_refresh_token,
            expiresIn=expires_in,
        )

    async def me(self, access_token: str) -> UserProfile:
        user = await self.current_user(access_token)
        return self._profile(user)

    async def current_user(self, access_token: str) -> UserModel:
        try:
            claims = decode_access_token(access_token)
            user_id = UUID(claims["sub"])
        except Exception:
            # FIX: any decode/parse failure -> clean 401, not a 500.
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=self.unauthorized
            ) from None

        if await self.repo.is_access_token_revoked(token_hash(access_token)):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=self.unauthorized
            )

        user = await self.repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=self.unauthorized
            )
        return user

    # ── Private helpers ─────────────────────────────────────────────────

    async def _create_refresh_token(
        self,
        user: UserModel,
        family_id: str | None = None,
    ) -> str:
        """Creates and persists a refresh token, returning the plaintext
        value to hand back to the client. Only the hash is stored."""
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
