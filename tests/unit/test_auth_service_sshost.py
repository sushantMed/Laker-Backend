from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.schemas.auth_schema import LoginRequest, LoginResponse
from app.services.auth_service import AuthService
from app.services.sshost_client import SSHostError


class DummyRedis:
    async def get(self, *_args, **_kwargs):
        return None

    async def delete(self, *_args, **_kwargs):
        return None

    async def pipeline(self, transaction=True):
        raise RuntimeError("not used")


@pytest.mark.asyncio
async def test_login_returns_tokens_on_valid_credentials(monkeypatch):
    monkeypatch.setattr(settings, "otp_enabled", False)
    service = AuthService(
        session=object(),
        redis=DummyRedis(),
        otp_secret="test-secret-not-a-sentinel",
    )

    user = SimpleNamespace(
        id="user-1",
        email="user@example.com",
        hashed_password="ignored",
        status="ACTIVE",
        role="user",
        first_name="Test",
        last_name="User",
    )

    async def fake_get_user_by_email(email):
        assert email == "user@example.com"
        return user

    async def fake_is_rate_limited(email, client_ip):
        return False

    async def fake_clear_attempts(email, client_ip):
        return None

    async def fake_verify_credentials(email, password, user_obj):
        assert email == "user@example.com"
        assert password == "secret123"
        return True

    async def fake_issue_tokens(user_obj):
        return LoginResponse(
            accessToken="access-token",
            refreshToken="refresh-token",
            tokenType="Bearer",
            expiresIn=3600,
        )

    monkeypatch.setattr(service.repo, "get_user_by_email", fake_get_user_by_email)
    monkeypatch.setattr(service, "_is_rate_limited", fake_is_rate_limited)
    monkeypatch.setattr(service, "_clear_attempts", fake_clear_attempts)
    monkeypatch.setattr(service, "_verify_credentials", fake_verify_credentials)
    monkeypatch.setattr(service, "_issue_tokens", fake_issue_tokens)

    response = await service.login(
        LoginRequest(email="user@example.com", password="secret123")
    )

    assert response.accessToken == "access-token"
    assert response.refreshToken == "refresh-token"


@pytest.mark.asyncio
async def test_login_falls_back_to_local_password_when_sshost_is_unreachable(
    monkeypatch,
):
    monkeypatch.setattr(settings, "otp_enabled", False)
    service = AuthService(session=object(), redis=DummyRedis())

    user = SimpleNamespace(
        id="user-2",
        email="fallback@example.com",
        hashed_password="local-hash",
        status="ACTIVE",
        role="user",
        first_name="Fallback",
        last_name="User",
        client_ip=None,
    )

    async def fake_get_user_by_email(email):
        assert email == "fallback@example.com"
        return user

    async def fake_authenticate(username, password):
        raise SSHostError("SSHost unreachable")

    async def fake_is_rate_limited(email, client_ip):
        return False

    async def fake_clear_attempts(email, client_ip):
        return None

    async def fake_create_refresh_token(user_obj, family_id=None):
        return "refresh-token"

    monkeypatch.setattr(service.repo, "get_user_by_email", fake_get_user_by_email)
    monkeypatch.setattr(service, "_is_rate_limited", fake_is_rate_limited)
    monkeypatch.setattr(service, "_clear_attempts", fake_clear_attempts)
    monkeypatch.setattr(service, "_create_refresh_token", fake_create_refresh_token)
    monkeypatch.setattr(
        "app.services.auth_service.authenticate_user", fake_authenticate
    )
    monkeypatch.setattr(
        "app.services.auth_service.verify_password", lambda password, stored_hash: True
    )

    response = await service.login(
        LoginRequest(email="fallback@example.com", password="secret123")
    )

    assert response.accessToken
    assert response.refreshToken == "refresh-token"
