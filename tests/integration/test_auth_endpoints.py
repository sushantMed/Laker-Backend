"""
Integration tests for /api/v1/auth

Endpoints:
  POST /api/v1/auth/login
  POST /api/v1/auth/logout
  POST /api/v1/auth/refresh
  GET  /api/v1/auth/me

Notes:
  - login/refresh catch all exceptions internally and return 200 with
    success=false on failure — no 4xx from these endpoints.
  - logout and me use real HTTPBearer — requires raw_client (no bearer override).
  - raw_client fixture is defined here since it's auth-specific.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis_client import get_redis
from app.database.session import get_db
from app.main import app

from .conftest import TestSessionLocal, _make_db_override

AUTH_BASE = "/api/v1/auth"


# ── raw_client: real bearer, test DB ─────────────────────────────────────────


@pytest_asyncio.fixture()
async def raw_client(
    db_session: AsyncSession, fake_redis
) -> AsyncGenerator[AsyncClient, None]:
    """Client with real bearer dependency — used for me/logout tests."""
    app.dependency_overrides[get_db] = _make_db_override(db_session)
    app.dependency_overrides[get_redis] = lambda: fake_redis

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ── seeded_user: creates a real user inside the test transaction ──────────────


@pytest_asyncio.fixture()
async def seeded_user(db_session: AsyncSession) -> dict:
    """
    Inserts a user into the test DB (inside the rollback transaction).
    Returns login credentials dict.
    """
    from app.core.security import hash_password
    from app.models.user_model import UserModel

    user = UserModel(
        email="test@example.com",
        first_name="Test",
        last_name="User",
        hashed_password=hash_password("Password1!"),
        role="user",
        status="ACTIVE",
    )
    db_session.add(user)
    await db_session.flush()
    return {"email": "test@example.com", "password": "Password1!"}


# ═════════════════════════════════════════════════════════════════════════════
# POST /api/v1/auth/login
# ═════════════════════════════════════════════════════════════════════════════


class TestLogin:
    async def test_login_success_returns_200(
        self, raw_client: AsyncClient, seeded_user: dict
    ):
        resp = await raw_client.post(f"{AUTH_BASE}/login", json=seeded_user)
        assert resp.status_code == 200

    async def test_login_success_response_shape(
        self, raw_client: AsyncClient, seeded_user: dict
    ):
        resp = await raw_client.post(f"{AUTH_BASE}/login", json=seeded_user)
        body = resp.json()
        assert body["success"] is True
        assert body["message"] == "Login successful"
        assert "data" in body

    async def test_login_returns_access_and_refresh_tokens(
        self, raw_client: AsyncClient, seeded_user: dict
    ):
        resp = await raw_client.post(f"{AUTH_BASE}/login", json=seeded_user)
        data = resp.json()["data"]
        assert "accessToken" in data
        assert "refreshToken" in data
        assert data["accessToken"] != ""
        assert data["refreshToken"] != ""

    async def test_login_returns_expires_in_and_token_type(
        self, raw_client: AsyncClient, seeded_user: dict
    ):
        data = (await raw_client.post(f"{AUTH_BASE}/login", json=seeded_user)).json()[
            "data"
        ]
        assert data["tokenType"] == "Bearer"
        assert isinstance(data["expiresIn"], int)
        assert data["expiresIn"] > 0

    async def test_login_wrong_password_returns_401(
        self, raw_client: AsyncClient, seeded_user: dict
    ):
        # invalid credentials → 401 with success=false envelope
        resp = await raw_client.post(
            f"{AUTH_BASE}/login",
            json={"email": seeded_user["email"], "password": "WrongPass1!"},
        )
        assert resp.status_code == 401
        assert resp.json()["success"] is False

    async def test_login_unknown_email_returns_404(self, raw_client: AsyncClient):
        resp = await raw_client.post(
            f"{AUTH_BASE}/login",
            json={"email": "nobody@example.com", "password": "Password1!"},
        )
        assert resp.status_code == 404
        assert resp.json()["success"] is False

    async def test_login_invalid_email_format_returns_422(
        self, raw_client: AsyncClient
    ):
        resp = await raw_client.post(
            f"{AUTH_BASE}/login",
            json={"email": "not-an-email", "password": "Password1!"},
        )
        assert resp.status_code == 422

    async def test_login_missing_password_returns_422(self, raw_client: AsyncClient):
        resp = await raw_client.post(
            f"{AUTH_BASE}/login",
            json={"email": "test@example.com"},
        )
        assert resp.status_code == 422

    async def test_login_password_too_short_returns_422(self, raw_client: AsyncClient):
        resp = await raw_client.post(
            f"{AUTH_BASE}/login",
            json={"email": "test@example.com", "password": "short"},
        )
        assert resp.status_code == 422


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/v1/auth/me
# ═════════════════════════════════════════════════════════════════════════════


class TestMe:
    async def test_me_no_auth_header_returns_403(self, raw_client: AsyncClient):
        resp = await raw_client.get(f"{AUTH_BASE}/me")
        assert resp.status_code == 403

    async def test_me_invalid_token_returns_200_success_false(
        self, raw_client: AsyncClient
    ):
        # me() catches exceptions — returns 200 success=false for bad token
        resp = await raw_client.get(
            f"{AUTH_BASE}/me",
            headers={"Authorization": "Bearer invalidtoken"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is False

    async def test_me_success_returns_user_profile(
        self, raw_client: AsyncClient, seeded_user: dict
    ):
        login = await raw_client.post(f"{AUTH_BASE}/login", json=seeded_user)
        token = login.json()["data"]["accessToken"]

        resp = await raw_client.get(
            f"{AUTH_BASE}/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_me_response_contains_user_fields(
        self, raw_client: AsyncClient, seeded_user: dict
    ):
        token = (await raw_client.post(f"{AUTH_BASE}/login", json=seeded_user)).json()[
            "data"
        ]["accessToken"]
        profile = (
            await raw_client.get(
                f"{AUTH_BASE}/me",
                headers={"Authorization": f"Bearer {token}"},
            )
        ).json()["data"]

        assert profile["email"] == seeded_user["email"]
        assert "userId" in profile
        assert "firstName" in profile
        assert "lastName" in profile
        assert "role" in profile
        assert "permissions" in profile

    async def test_me_after_logout_returns_success_false(
        self, raw_client: AsyncClient, seeded_user: dict
    ):
        token = (await raw_client.post(f"{AUTH_BASE}/login", json=seeded_user)).json()[
            "data"
        ]["accessToken"]

        await raw_client.post(
            f"{AUTH_BASE}/logout",
            headers={"Authorization": f"Bearer {token}"},
        )

        resp = await raw_client.get(
            f"{AUTH_BASE}/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is False


# ═════════════════════════════════════════════════════════════════════════════
# POST /api/v1/auth/refresh
# ═════════════════════════════════════════════════════════════════════════════


class TestRefresh:
    async def test_refresh_returns_new_token_pair(
        self, raw_client: AsyncClient, seeded_user: dict
    ):
        login = await raw_client.post(f"{AUTH_BASE}/login", json=seeded_user)
        refresh_token = login.json()["data"]["refreshToken"]

        resp = await raw_client.post(
            f"{AUTH_BASE}/refresh",
            json={"refreshToken": refresh_token},
        )

        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_refresh_token_is_rotated(
        self, raw_client: AsyncClient, seeded_user: dict
    ):
        login = await raw_client.post(f"{AUTH_BASE}/login", json=seeded_user)
        old_refresh = login.json()["data"]["refreshToken"]

        new_data = (
            await raw_client.post(
                f"{AUTH_BASE}/refresh",
                json={"refreshToken": old_refresh},
            )
        ).json()["data"]

        assert new_data["refreshToken"] != old_refresh

    async def test_refresh_response_has_required_fields(
        self, raw_client: AsyncClient, seeded_user: dict
    ):
        login = await raw_client.post(f"{AUTH_BASE}/login", json=seeded_user)
        data = (
            await raw_client.post(
                f"{AUTH_BASE}/refresh",
                json={"refreshToken": login.json()["data"]["refreshToken"]},
            )
        ).json()["data"]

        assert "accessToken" in data
        assert "refreshToken" in data
        assert "expiresIn" in data

    async def test_refresh_with_invalid_token_returns_success_false(
        self, raw_client: AsyncClient
    ):
        resp = await raw_client.post(
            f"{AUTH_BASE}/refresh",
            json={"refreshToken": "not-a-real-token"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is False

    async def test_refresh_token_cannot_be_reused(
        self, raw_client: AsyncClient, seeded_user: dict
    ):
        login = await raw_client.post(f"{AUTH_BASE}/login", json=seeded_user)
        old_refresh = login.json()["data"]["refreshToken"]

        # Use it once
        await raw_client.post(
            f"{AUTH_BASE}/refresh", json={"refreshToken": old_refresh}
        )

        # Reuse should fail
        resp = await raw_client.post(
            f"{AUTH_BASE}/refresh",
            json={"refreshToken": old_refresh},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is False

    async def test_refresh_missing_token_returns_422(self, raw_client: AsyncClient):
        resp = await raw_client.post(f"{AUTH_BASE}/refresh", json={})
        assert resp.status_code == 422


# ═════════════════════════════════════════════════════════════════════════════
# POST /api/v1/auth/logout
# ═════════════════════════════════════════════════════════════════════════════


class TestLogout:
    async def test_logout_no_auth_returns_403(self, raw_client: AsyncClient):
        resp = await raw_client.post(f"{AUTH_BASE}/logout")
        assert resp.status_code == 403

    async def test_logout_success_returns_204(
        self, raw_client: AsyncClient, seeded_user: dict
    ):
        token = (await raw_client.post(f"{AUTH_BASE}/login", json=seeded_user)).json()[
            "data"
        ]["accessToken"]

        resp = await raw_client.post(
            f"{AUTH_BASE}/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204

    async def test_logout_response_has_no_body(
        self, raw_client: AsyncClient, seeded_user: dict
    ):
        token = (await raw_client.post(f"{AUTH_BASE}/login", json=seeded_user)).json()[
            "data"
        ]["accessToken"]

        resp = await raw_client.post(
            f"{AUTH_BASE}/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.content == b""
