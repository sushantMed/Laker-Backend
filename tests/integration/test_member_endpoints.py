from __future__ import annotations

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.member_model import MemberModel
from app.models.plan_model import PlanModel
from app.utils.enums import CoverageType, Gender

from .conftest import BASE_PATH, _auth_header


def _make_plan(
    plan_id: str = "PLN001",
    carrier: str = "Acme Health",
    group_name: str | None = "Group A",
    group_number: str | None = "GRP-1",
    rx_bin: str | None = "123456",
    rx_pcn: str | None = "PCN1",
) -> PlanModel:
    return PlanModel(
        id=uuid.uuid4(),
        plan_id=plan_id,
        carrier=carrier,
        group_name=group_name,
        group_number=group_number,
        rx_bin=rx_bin,
        rx_pcn=rx_pcn,
    )


def _make_member(
    member_id: str = "MBR001",
    *,
    subscriber_member_id: str | None = None,
    first_name: str = "John",
    last_name: str = "Doe",
    mi: str | None = "A",
    date_of_birth: date = date(1980, 1, 1),
    gender: Gender | None = Gender.MALE,
    person_code: str = "01",
    family_position: str | None = "01",
    rel_code: str = "01",
    prev_card_id: str | None = None,
    cov_type: CoverageType | None = CoverageType.FAMILY,
    start_date: date = date(2020, 1, 1),
    end_date: date = date(2030, 1, 1),
    plan_id: str | None = None,
) -> MemberModel:
    return MemberModel(
        id=uuid.uuid4(),
        member_id=member_id,
        subscriber_member_id=subscriber_member_id,
        first_name=first_name,
        last_name=last_name,
        mi=mi,
        date_of_birth=date_of_birth,
        gender=gender,
        person_code=person_code,
        family_position=family_position,
        rel_code=rel_code,
        prev_card_id=prev_card_id,
        cov_type=cov_type,
        start_date=start_date,
        end_date=end_date,
        plan_id=plan_id,
    )


async def _seed(session: AsyncSession, *rows) -> None:
    session.add_all(rows)
    await session.flush()


class TestGetMember:
    def _url(self, member_id: str) -> str:
        return f"{BASE_PATH}/members/{member_id}"

    async def test_get_member_returns_member_detail(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(db_session, _make_plan(), _make_member(plan_id="PLN001"))

        resp = await client.get(self._url("MBR001"), headers=_auth_header())

        assert resp.status_code == 200, resp.json()
        body = resp.json()
        assert body["success"] is True
        assert body["message"] == "Member retrieved successfully."
        assert body["data"]["memberId"] == "MBR001"
        assert body["data"]["firstName"] == "John"
        assert body["data"]["plan"]["carrier"] == "Acme Health"

    async def test_get_member_not_found_returns_404(self, client: AsyncClient):
        resp = await client.get(self._url("MISSING"), headers=_auth_header())
        assert resp.status_code == 404

    async def test_get_member_is_case_insensitive(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(db_session, _make_member(member_id="MBR777"))

        resp = await client.get(self._url("mbr777"), headers=_auth_header())

        assert resp.status_code == 200
        assert resp.json()["data"]["memberId"] == "MBR777"


class TestSearchMembers:
    URL = f"{BASE_PATH}/members/search"

    async def test_search_by_last_name_returns_match(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(db_session, _make_member(member_id="MBR010", last_name="Anderson"))

        resp = await client.post(
            self.URL,
            json={"searchRequest": {"lastName": "Anderson"}},
            headers=_auth_header(),
        )

        assert resp.status_code == 200, resp.json()
        body = resp.json()
        ids = [r["memberId"] for r in body["data"]]
        assert "MBR010" in ids
        assert body["message"] == "Members retrieved successfully."

    async def test_search_no_match_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(db_session, _make_member(member_id="MBR011", last_name="Smith"))

        resp = await client.post(
            self.URL,
            json={"searchRequest": {"lastName": "Nobody"}},
            headers=_auth_header(),
        )

        assert resp.status_code == 404

    async def test_search_excludes_termed_members_by_default(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(
            db_session,
            _make_member(
                member_id="MBR-TERMED",
                last_name="Termed",
                start_date=date(2010, 1, 1),
                end_date=date(2015, 1, 1),
            ),
        )

        resp = await client.post(
            self.URL,
            json={"searchRequest": {"lastName": "Termed"}},
            headers=_auth_header(),
        )

        assert resp.status_code == 404

    async def test_search_includes_termed_when_flag_set(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(
            db_session,
            _make_member(
                member_id="MBR-TERMED2",
                last_name="Termed2",
                start_date=date(2010, 1, 1),
                end_date=date(2015, 1, 1),
            ),
        )

        resp = await client.post(
            self.URL,
            json={
                "searchRequest": {"lastName": "Termed2", "includeTermedMembers": True}
            },
            headers=_auth_header(),
        )

        assert resp.status_code == 200
        ids = [r["memberId"] for r in resp.json()["data"]]
        assert "MBR-TERMED2" in ids

    async def test_search_missing_search_request_returns_422(self, client: AsyncClient):
        resp = await client.post(
            self.URL,
            json={},
            headers=_auth_header(),
        )
        assert resp.status_code == 422


class TestEligibility:
    def _url(self, member_id: str) -> str:
        return f"{BASE_PATH}/members/{member_id}/eligibility"

    async def test_eligibility_returns_status(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(db_session, _make_member(member_id="MBR020"))

        resp = await client.get(self._url("MBR020"), headers=_auth_header())

        assert resp.status_code == 200, resp.json()
        body = resp.json()
        assert body["data"]["memberId"] == "MBR020"
        assert body["data"]["status"] == "ACTIVE"

    async def test_eligibility_not_found_returns_404(self, client: AsyncClient):
        resp = await client.get(self._url("MISSING"), headers=_auth_header())
        assert resp.status_code == 404


class TestGetFamily:
    def _url(self, member_id: str) -> str:
        return f"{BASE_PATH}/members/{member_id}/family"

    async def test_get_family_returns_unit(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(
            db_session,
            _make_member(member_id="MBR030", rel_code="01"),
            _make_member(
                member_id="MBR031",
                subscriber_member_id="MBR030",
                rel_code="03",
                person_code="02",
            ),
        )

        resp = await client.get(self._url("MBR030"), headers=_auth_header())

        assert resp.status_code == 200, resp.json()
        ids = [r["memberId"] for r in resp.json()["data"]]
        assert "MBR030" in ids
        assert "MBR031" in ids

    async def test_get_family_not_found_returns_404(self, client: AsyncClient):
        resp = await client.get(self._url("MISSING"), headers=_auth_header())
        assert resp.status_code == 404

    async def test_get_family_non_cardholder_returns_error(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(
            db_session,
            _make_member(
                member_id="MBR032", subscriber_member_id="MBR030", rel_code="03"
            ),
        )

        resp = await client.get(self._url("MBR032"), headers=_auth_header())

        assert resp.status_code == 422


class TestAddFamilyMember:
    def _url(self, member_id: str) -> str:
        return f"{BASE_PATH}/members/{member_id}/family"

    def _body(self, **overrides) -> dict:
        body = {
            "firstName": "Jane",
            "lastName": "Doe",
            "dateOfBirth": "1985-06-01",
            "relCode": "02",
            "covType": "Spouse",
            "startDate": "2020-01-01",
            "endDate": "2030-01-01",
        }
        body.update(overrides)
        return body

    async def test_add_family_member_success(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(db_session, _make_member(member_id="MBR040", rel_code="01"))

        resp = await client.post(
            self._url("MBR040"),
            json=self._body(relCode="03", covType="Dependent"),
            headers=_auth_header(),
        )

        assert resp.status_code == 201, resp.json()
        body = resp.json()
        assert body["data"]["firstName"] == "Jane"
        assert body["data"]["relCode"] == "03"

    async def test_add_family_member_subscriber_not_found(self, client: AsyncClient):
        resp = await client.post(
            self._url("MISSING"),
            json=self._body(relCode="03", covType="Dependent"),
            headers=_auth_header(),
        )
        assert resp.status_code == 404

    async def test_add_family_member_non_cardholder_subscriber(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(
            db_session,
            _make_member(
                member_id="MBR041", subscriber_member_id="MBR040", rel_code="03"
            ),
        )

        resp = await client.post(
            self._url("MBR041"),
            json=self._body(relCode="03", covType="Dependent"),
            headers=_auth_header(),
        )
        assert resp.status_code == 422

    async def test_add_second_spouse_returns_conflict(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(
            db_session,
            _make_member(member_id="MBR042", rel_code="01"),
            _make_member(
                member_id="MBR043",
                subscriber_member_id="MBR042",
                rel_code="02",
                person_code="02",
            ),
        )

        resp = await client.post(
            self._url("MBR042"),
            json=self._body(relCode="02", covType="Spouse"),
            headers=_auth_header(),
        )
        assert resp.status_code == 409

    async def test_add_family_member_missing_plan_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(db_session, _make_member(member_id="MBR044", rel_code="01"))

        resp = await client.post(
            self._url("MBR044"),
            json=self._body(relCode="03", covType="Dependent", planId="NO-PLAN"),
            headers=_auth_header(),
        )
        assert resp.status_code == 404

    async def test_add_family_member_missing_required_field_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(db_session, _make_member(member_id="MBR045", rel_code="01"))

        body = self._body(relCode="03", covType="Dependent")
        del body["firstName"]

        resp = await client.post(
            self._url("MBR045"),
            json=body,
            headers=_auth_header(),
        )
        assert resp.status_code == 422
