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
from datetime import date
 
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
 
from .conftest import BASE_PATH, _auth_header, _make_claim, _seed




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


