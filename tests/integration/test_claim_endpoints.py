import pytest
import pytest_asyncio
import httpx

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

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

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def get_test_client():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        yield client    

@pytest_asyncio.fixture(autouse=True)
async def test_search_claims(client):
    # Example test for the search_claims endpoint
    response = await client.post(
        "/api/v1/claims/search",
        json={"searchTerm": "example", "page": 1, "pageSize": 10}
    )
    assert response.status_code == 201
    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list)

@pytest_asyncio.fixture(autouse=True)
async def test_get_claim(client):
    # Example test for the get_claim endpoint
    auth_num = "12345"
    response = await client.get(f"/api/v1/claims/{auth_num}")
    assert response.status_code == 200
    data = response.json()
    assert "authNum" in data
    assert data["authNum"] == auth_num


@pytest_asyncio.fixture(autouse=True)
async def test_search_claims_for_member(client):
    # Example test for the search_claims_for_member endpoint
    member_id = "member123"
    response = await client.post(
        f"/api/v1/members/{member_id}/claims/search",
        json={"searchTerm": "example", "page": 1, "pageSize": 10}
    )
    assert response.status_code == 201
    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list)

@pytest_asyncio.fixture(autouse=True)
async def test_get_claims_for_member(client):
    # Example test for the get_claims_for_member endpoint
    member_id = "member123"
    response = await client.get(f"/api/v1/members/{member_id}/claims", params={"page": 1, "pageSize": 10})
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list)   




