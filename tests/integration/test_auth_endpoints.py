"""
Integration tests for /api/v1/auth
Uses pytest-anyio + httpx AsyncClient against a SQLite in-memory DB.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.base import Base
from app.database.session import get_db
from app.main import app

# ── SQLite in-memory engine for tests ────────────────────────────────────────

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSession() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def seeded_user(client):
    """Register a user directly in DB so we can test login."""
    from app.core.security import hash_password
    from app.models.user_model import UserModel

    async with TestSession() as session:
        user = UserModel(
            email="User@example.com",
            first_name="Test",
            last_name="User",
            hashed_password=hash_password("User@123"),
            role="user",
            status="ACTIVE",
        )
        session.add(user)
        await session.commit()
    return {"email": "User@example.com", "password": "User@123"}


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_success(client, seeded_user):
    resp = await client.post("/api/v1/auth/login", json=seeded_user)
    assert resp.status_code == 200
    data = resp.json()
    assert "accessToken" in data
    assert "refreshToken" in data
    assert data["user"]["email"] == seeded_user["email"]


@pytest.mark.asyncio
async def test_login_wrong_password(client, seeded_user):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": seeded_user["email"], "password": "WrongPass1!"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 403  # HTTPBearer returns 403 when no header


@pytest.mark.asyncio
async def test_me_success(client, seeded_user):
    login = await client.post("/api/v1/auth/login", json=seeded_user)
    token = login.json()["accessToken"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == seeded_user["email"]


@pytest.mark.asyncio
async def test_refresh_token_rotation(client, seeded_user):
    login = await client.post("/api/v1/auth/login", json=seeded_user)
    refresh_token = login.json()["refreshToken"]
    resp = await client.post("/api/v1/auth/refresh", json={"refreshToken": refresh_token})
    assert resp.status_code == 200
    new_data = resp.json()
    assert new_data["refreshToken"] != refresh_token  # rotated


@pytest.mark.asyncio
async def test_logout(client, seeded_user):
    login = await client.post("/api/v1/auth/login", json=seeded_user)
    token = login.json()["accessToken"]
    resp = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
