import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.constants import ACCESS_TOKEN_EXPIRE_SECONDS, ALGORITHM

SECRET_KEY = settings.jwt_secret_key


# ── Password ──────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return f"pbkdf2_sha256${salt}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, stored_hash: str) -> bool:
    if stored_hash.startswith("pbkdf2_sha256$"):
        _, salt, expected = stored_hash.split("$", 2)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
        actual = base64.urlsafe_b64encode(digest).decode()
        return hmac.compare_digest(actual, expected)
    return hmac.compare_digest(password, stored_hash)


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(*, subject: str, email: str, role: str) -> tuple[str, str, int]:
    now = int(time.time())
    jti = secrets.token_urlsafe(16)
    payload = {
        "sub": subject,
        "email": email,
        "role": role,
        "jti": jti,
        "iat": now,
        "exp": now + ACCESS_TOKEN_EXPIRE_SECONDS,
    }
    return _encode_jwt(payload), jti, ACCESS_TOKEN_EXPIRE_SECONDS


def decode_access_token(token: str, *, verify_exp: bool = True) -> dict[str, Any]:
    try:
        header, payload, signature = token.split(".")
        expected = _sign(f"{header}.{payload}")
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid token signature")
        claims = json.loads(_b64decode(payload))
        if verify_exp and int(claims["exp"]) < int(time.time()):
            raise ValueError("Token expired")
        return claims
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        ) from exc


def token_expires_at(token: str) -> datetime:
    claims = decode_access_token(token, verify_exp=False)
    return datetime.fromtimestamp(int(claims["exp"]), tz=timezone.utc)


# ── Opaque refresh tokens ─────────────────────────────────────────────────────

def opaque_token() -> str:
    return secrets.token_urlsafe(48)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ── Internal helpers ──────────────────────────────────────────────────────────

def _encode_jwt(payload: dict[str, Any]) -> str:
    header = {"alg": ALGORITHM, "typ": "JWT"}
    signing_input = f"{_b64encode(header)}.{_b64encode(payload)}"
    return f"{signing_input}.{_sign(signing_input)}"


def _sign(value: str) -> str:
    digest = hmac.new(SECRET_KEY.encode(), value.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def _b64encode(value: dict[str, Any]) -> str:
    raw = json.dumps(value, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
