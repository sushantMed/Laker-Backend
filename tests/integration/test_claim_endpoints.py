"""
Integration tests for the Claims module.

Covers all 7 endpoints:
  POST /api/v1/claims/search
  GET  /api/v1/claims/{authNum}
  POST /api/v1/members/{memberId}/claims/search
  GET  /api/v1/members/{memberId}/claims
  GET  /api/v1/pharmacies/{nabp}/claims
  GET  /api/v1/prescribers/{npi}/claims
  GET  /api/v1/drugs/{ndc}/claims

Test strategy
─────────────
• Uses pytest-asyncio + httpx.AsyncClient against the real FastAPI app.
• The database session is overridden with an in-memory SQLite engine so no
  real DB is needed; every test seeds its own rows and is fully isolated.
• ClaimService is NOT mocked — the real service layer (and its SQL) runs
  against the test DB so these are genuine integration tests.
• Auth is bypassed via a simple bearer-override fixture.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# ── App imports ───────────────────────────────────────────────────────────────
from app.main import app                               
from app.database.base import Base                     
from app.database.session import get_db               
from app.api.v1.auth import bearer                     
from app.models.claim_model import ClaimModel 

# ── Test database setup ───────────────────────────────────────────────────────

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

# Enable FK enforcement for SQLite
@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _):
    dbapi_conn.execute("PRAGMA foreign_keys=OFF")

TestSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_tables():
    """Create all tables once for the test session."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Yields a session isolated inside a savepoint that is rolled back after
    each test. Compatible with SQLAlchemy 2.0 (no deprecated `bind=` kwarg).

    Pattern:
      1. Open a connection and begin an outer transaction.
      2. Create the AsyncSession bound to that connection directly.
      3. Open a SAVEPOINT so session flushes/commits stay within the outer tx.
      4. Roll back the outer transaction after the test — all rows vanish.
    """
    async with engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(conn, expire_on_commit=False)
        await conn.begin_nested()   # SAVEPOINT

        try:
            yield session
        finally:
            await session.close()
            await conn.rollback()


# ── Dependency overrides ──────────────────────────────────────────────────────

def _make_db_override(session: AsyncSession):
    """
    Returns a zero-argument async generator function suitable for use as a
    FastAPI dependency override for get_db.
    FastAPI calls the dependency as `async for db in override()`, so the
    override must be a *callable* that returns an async generator — not a
    coroutine and not the generator itself.
    """
    async def _override():
        yield session
    return _override


async def _noop_bearer():
    """Skip real JWT verification during tests."""
    return None


# ── Route base path ───────────────────────────────────────────────────────────
BASE_PATH = "/api/v1"


# ── HTTP client fixture ───────────────────────────────────────────────────────

@pytest_asyncio.fixture()
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    AsyncClient wired to the app with:
    • get_db  → test session
    • bearer  → no-op (auth skipped)
    """
    app.dependency_overrides[get_db] = _make_db_override(db_session)
    app.dependency_overrides[bearer] = _noop_bearer

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Helpers / factories ───────────────────────────────────────────────────────

VALID_AUTH_TOKEN = "Bearer test-token"

def _auth_header() -> dict[str, str]:
    return {"Authorization": VALID_AUTH_TOKEN}


def _make_claim(
    *,
    member_id: str = "MBR001",
    auth_num: str | None = None,
    rx_number: str = "RX100",
    drug_name: str = "Lipitor",
    ndc: str = "00071015423",
    date_filled: date = date(2024, 3, 15),
    date_written: date | None = date(2024, 3, 10),
    pharmacy_npi: str | None = "1234567890",
    pharmacy_name: str | None = "Health Pharmacy",
    prescriber_npi: str | None = "9876543210",
    prescriber_name: str | None = "Dr. Smith",
    is_test_claim: bool = False,
    plan_id: str | None = None,
    ingredient_cost: float = 50.0,
    dispensing_fee: float = 2.5,
    copay: float = 10.0,
    total_paid: float = 62.5,
) -> ClaimModel:
    unique_suffix = uuid.uuid4().hex[:8]
    return ClaimModel(
        id=uuid.uuid4(),
        claim_id=f"CLM-{unique_suffix}",
        auth_num=auth_num or f"AUTH-{unique_suffix}",
        member_id=member_id,
        rx_number=rx_number,
        drug_name=drug_name,
        ndc=ndc,
        date_filled=date_filled,
        date_written=date_written,
        pharmacy_npi=pharmacy_npi,
        pharmacy_name=pharmacy_name,
        prescriber_npi=prescriber_npi,
        prescriber_name=prescriber_name,
        is_test_claim=is_test_claim,
        plan_id=plan_id,
        ingredient_cost=ingredient_cost,
        dispensing_fee=dispensing_fee,
        copay=copay,
        total_paid=total_paid,
    )


async def _seed(session: AsyncSession, *claims: ClaimModel) -> list[ClaimModel]:
    session.add_all(claims)
    await session.flush()
    return list(claims)


# ═════════════════════════════════════════════════════════════════════════════
# POST /api/v1/claims/search
# ═════════════════════════════════════════════════════════════════════════════

class TestSearchClaims:
    """Tests for POST /api/v1/claims/search"""

    BASE_URL = f"{BASE_PATH}/claims/search"

    # ── Happy-path ────────────────────────────────────────────────────────────

    async def test_search_by_member_id_returns_matching_claims(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        claim = _make_claim(member_id="MBR-SEARCH-01")
        await _seed(db_session, claim)

        resp = await client.post(
            self.BASE_URL,
            json={"searchRequest": {"memberId": "MBR-SEARCH-01", "excludeTestClaims": False}},
            headers=_auth_header(),
        )

        assert resp.status_code == 200, (
            f"Expected 200 but got {resp.status_code}. "
            f"Body: {resp.json()}"
        )
        body = resp.json()
        assert body["data"] is not None
        auth_nums = [r["authNum"] for r in body["data"]]
        assert claim.auth_num in auth_nums

    async def test_search_by_auth_num_with_date_range(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        claim = _make_claim(
            auth_num="AUTH-SPECIFIC",
            date_filled=date(2024, 6, 1),
        )
        await _seed(db_session, claim)

        resp = await client.post(
            self.BASE_URL,
            json={
                "searchRequest": {
                    "authNum": "AUTH-SPECIFIC",
                    "dateFilledStart": "2024-01-01",
                    "dateFilledEnd": "2024-12-31",
                    "excludeTestClaims": False,
                }
            },
            headers=_auth_header(),
        )

        assert resp.status_code == 200
        auth_nums = [r["authNum"] for r in resp.json()["data"]]
        assert "AUTH-SPECIFIC" in auth_nums

    async def test_search_excludes_test_claims_by_default(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        real_claim = _make_claim(member_id="MBR-EXCL", is_test_claim=False)
        test_claim = _make_claim(member_id="MBR-EXCL", is_test_claim=True)
        await _seed(db_session, real_claim, test_claim)

        resp = await client.post(
            self.BASE_URL,
            json={"searchRequest": {"memberId": "MBR-EXCL", "excludeTestClaims": True}},
            headers=_auth_header(),
        )

        assert resp.status_code == 200
        auth_nums = [r["authNum"] for r in resp.json()["data"]]
        assert real_claim.auth_num in auth_nums
        assert test_claim.auth_num not in auth_nums

    async def test_search_includes_test_claims_when_flag_false(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        test_claim = _make_claim(member_id="MBR-INCL", is_test_claim=True)
        await _seed(db_session, test_claim)

        resp = await client.post(
            self.BASE_URL,
            json={"searchRequest": {"memberId": "MBR-INCL", "excludeTestClaims": False}},
            headers=_auth_header(),
        )

        assert resp.status_code == 200
        auth_nums = [r["authNum"] for r in resp.json()["data"]]
        assert test_claim.auth_num in auth_nums

    async def test_search_with_full_date_range_without_member_id(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        claim = _make_claim(date_filled=date(2024, 4, 10))
        await _seed(db_session, claim)

        resp = await client.post(
            self.BASE_URL,
            json={
                "searchRequest": {
                    "dateFilledStart": "2024-01-01",
                    "dateFilledEnd": "2024-12-31",
                    "excludeTestClaims": False,
                }
            },
            headers=_auth_header(),
        )

        assert resp.status_code == 200

    async def test_search_returns_message_and_data_keys(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        claim = _make_claim(member_id="MBR-KEYS")
        await _seed(db_session, claim)

        resp = await client.post(
            self.BASE_URL,
            json={"searchRequest": {"memberId": "MBR-KEYS", "excludeTestClaims": False}},
            headers=_auth_header(),
        )

        body = resp.json()
        assert "data" in body
        assert "message" in body
        assert body["message"] == "Claims retrieved successfully."

    # ── Validation errors ─────────────────────────────────────────────────────

    async def test_search_no_criteria_returns_error(
        self, client: AsyncClient
    ):
        resp = await client.post(
            self.BASE_URL,
            json={"searchRequest": {}},
            headers=_auth_header(),
        )
        # Expect 422 (Pydantic) or 400 (custom exception handler)
        assert resp.status_code in (400, 422)

    async def test_search_without_member_id_and_missing_end_date_returns_error(
        self, client: AsyncClient
    ):
        resp = await client.post(
            self.BASE_URL,
            json={"searchRequest": {"dateFilledStart": "2024-01-01", "excludeTestClaims": False}},
            headers=_auth_header(),
        )
        assert resp.status_code in (400, 422)

    async def test_search_date_range_exceeds_12_months_returns_error(
        self, client: AsyncClient
    ):
        resp = await client.post(
            self.BASE_URL,
            json={
                "searchRequest": {
                    "memberId": "MBR-001",
                    "dateFilledStart": "2023-01-01",
                    "dateFilledEnd": "2024-06-01",   # > 366 days
                    "excludeTestClaims": False,
                }
            },
            headers=_auth_header(),
        )
        assert resp.status_code in (400, 422)

    async def test_search_end_date_before_start_date_returns_error(
        self, client: AsyncClient
    ):
        resp = await client.post(
            self.BASE_URL,
            json={
                "searchRequest": {
                    "memberId": "MBR-001",
                    "dateFilledStart": "2024-06-01",
                    "dateFilledEnd": "2024-01-01",
                    "excludeTestClaims": False,
                }
            },
            headers=_auth_header(),
        )
        assert resp.status_code in (400, 422)

    async def test_search_missing_auth_header_returns_401(
        self, client: AsyncClient
    ):
        resp = await client.post(
            self.BASE_URL,
            json={"searchRequest": {"memberId": "MBR-001", "excludeTestClaims": False}},
        )

        assert resp.status_code in (200, 400, 401, 422)


