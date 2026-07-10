"""Unit tests for core/security.py"""

import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    opaque_token,
    token_hash,
    verify_password,
)


def test_password_round_trip():
    raw = "Sup3r$ecret!"
    hashed = hash_password(raw)
    assert hashed != raw
    assert verify_password(raw, hashed)
    assert not verify_password("wrong", hashed)


def test_jwt_round_trip():
    token, jti, expires_in = create_access_token(
        subject="1", email="a@b.com", role="user"
    )
    claims = decode_access_token(token)
    assert claims["sub"] == "1"
    assert claims["email"] == "a@b.com"
    assert claims["role"] == "user"
    assert "jti" in claims


def test_jwt_tampered_signature_rejected():
    token, _, _ = create_access_token(subject="1", email="a@b.com", role="user")
    header, payload, sig = token.split(".")
    bad_token = f"{header}.{payload}.invalidsig"
    with pytest.raises(Exception):
        decode_access_token(bad_token)


def test_opaque_token_unique():
    t1, t2 = opaque_token(), opaque_token()
    assert t1 != t2


def test_token_hash_deterministic():
    t = opaque_token()
    assert token_hash(t) == token_hash(t)
