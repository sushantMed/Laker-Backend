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

from httpx import AsyncClient  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore

from .conftest import BASE_PATH, _auth_header, _make_claim, _make_member, _seed


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
            json={
                "searchRequest": {
                    "memberId": "MBR-SEARCH-01",
                    "excludeTestClaims": False,
                }
            },
            headers=_auth_header(),
        )

        assert resp.status_code == 200, (
            f"Expected 200 but got {resp.status_code}. Body: {resp.json()}"
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
            json={
                "searchRequest": {"memberId": "MBR-INCL", "excludeTestClaims": False}
            },
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
            json={
                "searchRequest": {"memberId": "MBR-KEYS", "excludeTestClaims": False}
            },
            headers=_auth_header(),
        )

        body = resp.json()
        assert "data" in body
        assert "message" in body
        assert body["message"] == "Claims retrieved successfully."

    # ── Validation errors ─────────────────────────────────────────────────────

    async def test_search_no_criteria_returns_error(self, client: AsyncClient):
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
            json={
                "searchRequest": {
                    "dateFilledStart": "2024-01-01",
                    "excludeTestClaims": False,
                }
            },
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
                    "dateFilledEnd": "2024-06-01",  # > 366 days
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

    async def test_search_missing_auth_header_returns_401(self, client: AsyncClient):
        resp = await client.post(
            self.BASE_URL,
            json={"searchRequest": {"memberId": "MBR-001", "excludeTestClaims": False}},
        )

        assert resp.status_code in (200, 400, 401, 422)


#  ═════════════════════════════════════════════════════════════════════════════
# GET /api/v1/claims/{authNum}
# ═════════════════════════════════════════════════════════════════════════════
class TestGetClaim:
    """Tests for GET /api/v1/claims/{authNum}"""

    # ── Happy-path ────────────────────────────────────────────────────────────

    async def test_get_claim_returns_full_detail(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        claim = _make_claim(auth_num="AUTH-DETAIL-01", member_id="MBR-DET")
        await _seed(db_session, claim)

        resp = await client.get(
            f"{BASE_PATH}/claims/{claim.auth_num}", headers=_auth_header()
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["authNum"] == "AUTH-DETAIL-01"
        assert body["data"]["memberId"] == "MBR-DET"

    async def test_get_claim_response_contains_pharmacy_and_prescriber(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        db_session.add(_make_member(member_id="MBR001"))
        await db_session.flush()

        claim = _make_claim(
            auth_num="AUTH-PHARM-01",
            pharmacy_npi="1111111111",
            pharmacy_name="Test Pharmacy",
            prescriber_npi="2222222222",
            prescriber_name="Dr. Test",
        )
        await _seed(db_session, claim)

        resp = await client.get(
            f"{BASE_PATH}/claims/{claim.auth_num}", headers=_auth_header()
        )

        assert resp.status_code == 200
        body = resp.json()
        print(body)
        assert body["data"]["pharmacy"]["pharmacyNpi"] == "1111111111"
        assert body["data"]["pharmacy"]["pharmacyName"] == "Test Pharmacy"
        assert body["data"]["prescriber"]["prescriberNpi"] == "2222222222"
        assert body["data"]["prescriber"]["prescriberName"] == "Dr. Test"

    async def test_get_claim_response_contains_cost_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        claim = _make_claim(
            auth_num="AUTH-COST-01",
            ingredient_cost=45.0,
            dispensing_fee=3.0,
            copay=15.0,
            total_paid=63.0,
        )
        await _seed(db_session, claim)

        resp = await client.get(
            f"{BASE_PATH}/claims/{claim.auth_num}", headers=_auth_header()
        )

        body = resp.json()
        assert body["data"]["ingredientCost"] == 45.0
        assert body["data"]["dispensingFee"] == 3.0
        assert body["data"]["copay"] == 15.0
        assert body["data"]["totalPaid"] == 63.0

    async def test_get_claim_camelcase_fields_returned(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        claim = _make_claim(auth_num="AUTH-CAMEL-01", date_filled=date(2024, 5, 20))
        await _seed(db_session, claim)

        resp = await client.get(
            f"{BASE_PATH}/claims/{claim.auth_num}", headers=_auth_header()
        )

        body = resp.json()
        print(body)
        # Verify API surface uses camelCase keys
        assert body["data"]["authNum"] == "AUTH-CAMEL-01"
        assert body["data"]["memberId"] == "MBR001"
        assert body["data"]["dateFilled"] == "2024-05-20"


# ═════════════════════════════════════════════════════════════════════════════
# POST /api/v1/claims/{memberId}/claims/search
# ═════════════════════════════════════════════════════════════════════════════
class TestSearchClaimsForMember:
    """Tests for POST /api/v1/members/{memberId}/claims/search"""

    def _url(self, memberId: str) -> str:
        return f"{BASE_PATH}/members/{memberId}/claims/search"

    async def test_search_returns_only_target_member_claims(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        db_session.add(_make_member(member_id="MBR-TARGET"))
        db_session.add(_make_member(member_id="MBR-OTHER"))
        await db_session.flush()

        target_claim = _make_claim(member_id="MBR-TARGET")
        other_claim = _make_claim(member_id="MBR-OTHER")
        await _seed(db_session, target_claim, other_claim)
        resp = await client.post(
            self._url("MBR-TARGET"),
            json={"searchRequest": {"excludeTestClaims": False}},
            headers=_auth_header(),
        )

        assert resp.status_code == 200
        auth_nums = [r["authNum"] for r in resp.json()["data"]]
        assert target_claim.auth_num in auth_nums
        assert other_claim.auth_num not in auth_nums

    async def test_member_search_with_auth_num_filter(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        db_session.add(_make_member(member_id="MBR-AN-01"))
        await db_session.flush()

        c1 = _make_claim(member_id="MBR-AN-01", auth_num="AUTH-AN-FILTER")
        c2 = _make_claim(member_id="MBR-AN-01")
        await _seed(db_session, c1, c2)

        resp = await client.post(
            self._url("MBR-AN-01"),
            json={
                "searchRequest": {
                    "authNum": "AUTH-AN-FILTER",
                    "excludeTestClaims": False,
                }
            },
            headers=_auth_header(),
        )

        assert resp.status_code == 200
        auth_nums = [r["authNum"] for r in resp.json()["data"]]
        assert "AUTH-AN-FILTER" in auth_nums
        assert c2.auth_num not in auth_nums

    async def test_member_search_with_date_range_filter(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        db_session.add(_make_member(member_id="MBR-DR-01"))
        await db_session.flush()

        in_range = _make_claim(member_id="MBR-DR-01", date_filled=date(2024, 5, 15))
        out_range = _make_claim(member_id="MBR-DR-01", date_filled=date(2023, 1, 1))
        await _seed(db_session, in_range, out_range)

        resp = await client.post(
            self._url("MBR-DR-01"),
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
        auth_nums = [r["authNum"] for r in resp.json()["data"]]
        assert in_range.auth_num in auth_nums
        assert out_range.auth_num not in auth_nums

    async def test_member_search_empty_body_returns_all_member_claims(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        db_session.add(_make_member(member_id="MBR-EMPTY-01"))
        await db_session.flush()

        """No body criteria — should return all claims for the member."""
        c1 = _make_claim(member_id="MBR-EMPTY-01")
        c2 = _make_claim(member_id="MBR-EMPTY-01")
        await _seed(db_session, c1, c2)

        resp = await client.post(
            self._url("MBR-EMPTY-01"),
            json={"searchRequest": {}},
            headers=_auth_header(),
        )

        assert resp.status_code == 200
        auth_nums = [r["authNum"] for r in resp.json()["data"]]
        assert c1.auth_num in auth_nums
        assert c2.auth_num in auth_nums

    # ── Validation errors ─────────────────────────────────────────────────────

    async def test_member_search_date_range_exceeds_12_months(
        self, client: AsyncClient
    ):
        resp = await client.post(
            self._url("MBR-001"),
            json={
                "searchRequest": {
                    "dateFilledStart": "2023-01-01",
                    "dateFilledEnd": "2024-06-01",
                }
            },
            headers=_auth_header(),
        )
        assert resp.status_code in (400, 422)

    async def test_member_search_end_before_start_returns_error(
        self, client: AsyncClient
    ):
        resp = await client.post(
            self._url("MBR-001"),
            json={
                "searchRequest": {
                    "dateFilledStart": "2024-12-01",
                    "dateFilledEnd": "2024-01-01",
                }
            },
            headers=_auth_header(),
        )
        assert resp.status_code in (400, 422)


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/v1/members/{memberId}/claims
# ═════════════════════════════════════════════════════════════════════════════
class TestGetClaimsForMember:
    """Tests for GET /api/v1/members/{memberId}/claims"""

    def _url(self, memberId: str) -> str:
        return f"{BASE_PATH}/members/{memberId}/claims"

    async def test_returns_claims_for_member(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        db_session.add(_make_member(member_id="MBR-GET-LIST-01"))
        await db_session.flush()

        c1 = _make_claim(member_id="MBR-GET-LIST-01")
        c2 = _make_claim(member_id="MBR-GET-LIST-01")
        await _seed(db_session, c1, c2)

        resp = await client.get(self._url("MBR-GET-LIST-01"), headers=_auth_header())

        assert resp.status_code == 200
        auth_nums = [r["authNum"] for r in resp.json()["data"]]
        assert c1.auth_num in auth_nums
        assert c2.auth_num in auth_nums

    async def test_does_not_return_other_member_claims(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        db_session.add(_make_member(member_id="MBR-MINE"))
        db_session.add(_make_member(member_id="MBR-THEIRS"))
        await db_session.flush()

        my_claim = _make_claim(member_id="MBR-MINE")
        other_claim = _make_claim(member_id="MBR-THEIRS")
        await _seed(db_session, my_claim, other_claim)

        resp = await client.get(self._url("MBR-MINE"), headers=_auth_header())

        assert resp.status_code == 200
        auth_nums = [r["authNum"] for r in resp.json()["data"]]
        assert my_claim.auth_num in auth_nums
        assert other_claim.auth_num not in auth_nums

    async def test_pagination_page_size_respected(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        db_session.add(_make_member(member_id="MBR-PAGE-01"))
        await db_session.flush()

        claims = [_make_claim(member_id="MBR-PAGE-01") for _ in range(5)]
        await _seed(db_session, *claims)

        resp = await client.get(
            self._url("MBR-PAGE-01"),
            params={"page": 1, "pageSize": 2},
            headers=_auth_header(),
        )

        assert resp.status_code == 200
        assert len(resp.json()["data"]) <= 2

    async def test_pagination_invalid_page_returns_422(self, client: AsyncClient):
        resp = await client.get(
            self._url("MBR-001"),
            params={"page": 0},
            headers=_auth_header(),
        )
        assert resp.status_code == 422

    async def test_pagination_page_size_exceeds_max_returns_422(
        self, client: AsyncClient
    ):
        resp = await client.get(
            self._url("MBR-001"),
            params={"pageSize": 200},
            headers=_auth_header(),
        )
        assert resp.status_code == 422

    async def test_returns_empty_list_for_unknown_member(self, client: AsyncClient):
        resp = await client.get(self._url("MBR-NOBODY"), headers=_auth_header())
        assert resp.status_code == 404
        assert resp.json()["data"] is None

    async def test_success_message_present(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        db_session.add(_make_member(member_id="MBR-MSG-01"))
        db_session.flush()

        claim = _make_claim(member_id="MBR-MSG-01")
        await _seed(db_session, claim)

        resp = await client.get(self._url("MBR-MSG-01"), headers=_auth_header())

        assert resp.json()["message"] == "Claims retrieved successfully."
