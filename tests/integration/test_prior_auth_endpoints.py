from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.drug_model import DrugModel
from app.models.member_model import MemberModel
from app.models.plan_model import PlanModel
from app.models.prescriber_model import PrescriberModel
from app.models.prior_auth_model import PriorAuthModel
from app.utils.enums import BrandGeneric, Maintenance
from tests.integration.conftest import AUTH

BASE = "/api/v1"
TODAY = date.today()
FUTURE = TODAY + timedelta(days=200)
PAST = TODAY - timedelta(days=200)


def make_pa(authnum: int, **overrides) -> PriorAuthModel:
    values = {
        "id": uuid.uuid4(),
        "authnum": Decimal(authnum),
        "subscribernum": "INS001",
        "groupnum": "GRP001",
        "personcodes": "01",
        "effdate": TODAY - timedelta(days=30),
        "termdate": FUTURE,
        "providerid": "2400214",
        "prescriberid": "1112223334",
        "ndc": "00074312811",
        "gpi": "27250030100120",
        "bg": "B",
        "action": "A",
        "genname": "ADALIMUMAB",
        "authby": "DR. ANITA PATEL",
    }
    values.update(overrides)
    return PriorAuthModel(**values)


@pytest_asyncio.fixture()
async def seeded_pa(db_session: AsyncSession, seeded_lookups):
    plan = PlanModel(
        plan_id="PLN001",
        carrier="BlueCross",
        group_name="Acme",
        group_number="GRP001",
    )
    db_session.add(plan)
    await db_session.flush()

    db_session.add_all(
        [
            MemberModel(
                id=uuid.uuid4(),
                member_id="MBR001",
                first_name="Carlos",
                last_name="Martinez",
                date_of_birth=date(1978, 4, 12),
                person_code="01",
                rel_code="01",
                start_date=date(2023, 1, 1),
                end_date=date(2099, 12, 31),
                insured_id="INS001",
                plan_id="PLN001",
            ),
            MemberModel(
                id=uuid.uuid4(),
                member_id="MBR002",
                first_name="Sofia",
                last_name="Martinez",
                date_of_birth=date(1980, 9, 25),
                person_code="02",
                rel_code="02",
                start_date=date(2023, 1, 1),
                end_date=date(2099, 12, 31),
                insured_id="INS001",
                plan_id="PLN001",
            ),
            MemberModel(
                id=uuid.uuid4(),
                member_id="MBR003",
                first_name="Minh",
                last_name="Nguyen",
                date_of_birth=date(1990, 2, 2),
                person_code="01",
                rel_code="01",
                start_date=date(2023, 1, 1),
                end_date=date(2099, 12, 31),
                insured_id="INS003",
                plan_id="PLN001",
            ),
        ]
    )
    db_session.add_all(
        [
            make_pa(2001),
            make_pa(
                2002,
                personcodes="02",
                ndc="00093721410",
                gpi="39400010100310",
                genname="ATORVASTATIN CALCIUM",
                bg="G",
                effdate=date(2026, 3, 1),
            ),
            make_pa(2003, action=None, authby=None, prescriberid=None),
            make_pa(2004, action="D", denial="03"),
            make_pa(2005, termdate=PAST),
            make_pa(
                2006,
                subscribernum="INS003",
                personcodes="01,02",
                ndc=None,
                genname=None,
                manualgenname="COMPOUNDED CREAM",
            ),
        ]
    )
    await db_session.flush()


async def search(client, body: dict, path: str = "/prior-auth/search"):
    return await client.post(f"{BASE}{path}", json=body, headers=AUTH)


@pytest.mark.asyncio
async def test_search_by_ndc(client, seeded_pa):
    resp = await search(client, {"searchRequest": {"ndc": "00074312811"}})

    assert resp.status_code == 200
    body = resp.json()
    assert body["pagination"]["total"] == 4
    assert {row["ndc"] for row in body["data"]} == {"00074312811"}


@pytest.mark.asyncio
async def test_search_resolves_member_details(client, seeded_pa):
    resp = await search(client, {"searchRequest": {"paId": "2001"}})

    row = resp.json()["data"][0]
    assert row["paId"] == "2001"
    assert row["memberId"] == "MBR001"
    assert row["firstName"] == "Carlos"
    assert row["lastName"] == "Martinez"
    assert row["drugName"] == "Humira"
    assert row["provider"] == "Dr. Jane Smith"
    assert row["status"] == "Authorized"


# @pytest.mark.asyncio
# async def test_search_by_member_id_uses_insured_id_and_person_code(client, seeded_pa):
#     resp = await search(client, {"searchRequest": {"memberId": "MBR002"}})
#
#     body = resp.json()
#     assert body["pagination"]["total"] == 1
#     assert body["data"][0]["paId"] == "2002"


@pytest.mark.asyncio
async def test_search_by_unknown_member_id_falls_back_to_subscribernum(
    client, seeded_pa
):
    resp = await search(client, {"searchRequest": {"memberId": "INS003"}})

    assert resp.status_code == 200
    assert resp.json()["pagination"]["total"] == 1


# @pytest.mark.asyncio
# @pytest.mark.parametrize(
#     ("status", "expected"),
#     [
#         ("Authorized", {"2001", "2002", "2006"}),
#         ("Pending", {"2003"}),
#         ("Declined", {"2004"}),
#         ("Expired", {"2005"}),
#     ],
# )
# async def test_search_by_status(client, seeded_pa, status, expected):
#     resp = await search(client, {"searchRequest": {"status": status}})
#
#     assert resp.status_code == 200
#     assert {row["paId"] for row in resp.json()["data"]} == expected


# @pytest.mark.asyncio
# async def test_search_status_filter_agrees_with_rendered_status(client, seeded_pa):
#     resp = await search(client, {"searchRequest": {"status": "Expired"}})
#
#     assert [row["status"] for row in resp.json()["data"]] == ["Expired"]


@pytest.mark.asyncio
async def test_search_by_drug_name_matches_catalogue(client, seeded_pa):
    resp = await search(client, {"searchRequest": {"drugName": "humira"}})

    assert resp.json()["pagination"]["total"] == 4


@pytest.mark.asyncio
async def test_search_by_drug_name_matches_manual_name(client, seeded_pa):
    resp = await search(client, {"searchRequest": {"drugName": "COMPOUNDED"}})

    body = resp.json()
    assert body["pagination"]["total"] == 1
    assert body["data"][0]["drugName"] == "COMPOUNDED CREAM"


# @pytest.mark.asyncio
# async def test_search_by_eff_date_range(client, seeded_pa):
#     resp = await search(
#         client,
#         {
#             "searchRequest": {
#                 "effDateFrom": "02/01/2026",
#                 "effDateTo": "04/01/2026",
#             }
#         },
#     )
#
#     body = resp.json()
#     assert body["pagination"]["total"] == 1
#     assert body["data"][0]["paId"] == "2002"


@pytest.mark.asyncio
async def test_search_without_criteria_is_rejected(client, seeded_pa):
    resp = await search(client, {"searchRequest": {}})

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_search_with_reversed_date_range_is_rejected(client, seeded_pa):
    resp = await search(
        client,
        {"searchRequest": {"effDateFrom": "12/31/2026", "effDateTo": "01/01/2026"}},
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_paginates_and_sorts(client, seeded_pa):
    resp = await search(
        client,
        {
            "searchRequest": {"ndc": "00074312811"},
            "sort": {"sortBy": "paId", "sortDir": "DESC"},
            "pagination": {"page": 1, "pageSize": 2},
        },
    )

    body = resp.json()
    assert body["pagination"]["total"] == 4
    assert body["pagination"]["totalPages"] == 2
    assert [row["paId"] for row in body["data"]] == ["2005", "2004"]


@pytest.mark.asyncio
async def test_search_second_page(client, seeded_pa):
    resp = await search(
        client,
        {
            "searchRequest": {"ndc": "00074312811"},
            "sort": {"sortBy": "paId", "sortDir": "ASC"},
            "pagination": {"page": 2, "pageSize": 2},
        },
    )

    assert [row["paId"] for row in resp.json()["data"]] == ["2004", "2005"]


@pytest.mark.asyncio
async def test_search_returns_empty_page_when_nothing_matches(client, seeded_pa):
    resp = await search(client, {"searchRequest": {"ndc": "99999999999"}})

    assert resp.status_code == 200
    assert resp.json()["data"] == []


@pytest.mark.asyncio
async def test_get_prior_auth_detail(client, seeded_pa):
    resp = await client.get(f"{BASE}/prior-auth/2001", headers=AUTH)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["paId"] == "2001"
    assert data["groupNumber"] == "GRP001"
    assert data["personCodes"] == "01"
    assert data["pharmacyNabp"] == "2400214"
    assert data["prescriberNpi"] == "1112223334"


@pytest.mark.asyncio
async def test_get_prior_auth_not_found(client, seeded_pa):
    resp = await client.get(f"{BASE}/prior-auth/9999", headers=AUTH)

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_prior_auth_with_non_numeric_id(client, seeded_pa):
    resp = await client.get(f"{BASE}/prior-auth/abc", headers=AUTH)

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_family_pa_resolves_to_lowest_person_code(client, seeded_pa):
    resp = await client.get(f"{BASE}/prior-auth/2006", headers=AUTH)

    data = resp.json()["data"]
    assert data["personCodes"] == "01,02"
    assert data["memberId"] == "MBR003"


@pytest.mark.asyncio
async def test_create_prior_auth(client, seeded_pa):
    resp = await client.post(
        f"{BASE}/prior-auth",
        json={
            "memberId": "MBR001",
            "effDate": "09/01/2026",
            "termDate": "08/31/2027",
            "drugName": "HUMIRA",
            "ndc": "00074312811",
            "status": "Authorized",
            "reasonCode": "SPECIALTY",
            "notes": "created by test",
            "diagnosis": "M06.9",
        },
        headers=AUTH,
    )

    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["paId"] == "2007"
    assert data["memberId"] == "MBR001"
    assert data["groupNumber"] == "GRP001"
    assert data["status"] == "Authorized"
    assert data["reasonCode"] == "SPECIALTY"
    assert data["createdBy"] == "tester@example.com"[:20]


@pytest.mark.asyncio
async def test_created_pa_is_retrievable(client, seeded_pa):
    created = await client.post(
        f"{BASE}/prior-auth",
        json={
            "memberId": "MBR001",
            "effDate": "09/01/2026",
            "termDate": "08/31/2027",
            "drugName": "HUMIRA",
            "ndc": "00074312811",
            "status": "Pending",
        },
        headers=AUTH,
    )
    pa_id = created.json()["data"]["paId"]

    resp = await client.get(f"{BASE}/prior-auth/{pa_id}", headers=AUTH)

    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "Pending"


@pytest.mark.asyncio
async def test_create_rejects_unknown_member(client, seeded_pa):
    resp = await client.post(
        f"{BASE}/prior-auth",
        json={
            "memberId": "MBR999",
            "effDate": "09/01/2026",
            "termDate": "08/31/2027",
            "drugName": "HUMIRA",
            "ndc": "00074312811",
            "status": "Authorized",
        },
        headers=AUTH,
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_rejects_unknown_ndc(client, seeded_pa):
    resp = await client.post(
        f"{BASE}/prior-auth",
        json={
            "memberId": "MBR001",
            "effDate": "09/01/2026",
            "termDate": "08/31/2027",
            "drugName": "HUMIRA",
            "ndc": "11111111111",
            "status": "Authorized",
        },
        headers=AUTH,
    )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_rejects_reversed_dates(client, seeded_pa):
    resp = await client.post(
        f"{BASE}/prior-auth",
        json={
            "memberId": "MBR001",
            "effDate": "09/01/2027",
            "termDate": "08/31/2026",
            "drugName": "HUMIRA",
            "ndc": "00074312811",
            "status": "Authorized",
        },
        headers=AUTH,
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_prior_auth(client, seeded_pa):
    resp = await client.put(
        f"{BASE}/prior-auth/2003",
        json={
            "effDate": "01/01/2026",
            "termDate": "12/31/2027",
            "drugName": "HUMIRA REPLACED",
            "ndc": "00074312811",
            "status": "Authorized",
            "reasonCode": "SPECIALTY",
            "notes": "replaced",
            "diagnosis": "L40.0",
        },
        headers=AUTH,
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "Authorized"
    assert data["notes"] == "replaced"
    assert data["changedBy"] == "tester@example.com"[:20]


@pytest.mark.asyncio
async def test_update_rejects_expired_pa(client, seeded_pa):
    resp = await client.put(
        f"{BASE}/prior-auth/2005",
        json={
            "effDate": "01/01/2026",
            "termDate": "12/31/2027",
            "drugName": "HUMIRA",
            "ndc": "00074312811",
            "status": "Authorized",
        },
        headers=AUTH,
    )

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_rejects_invalid_transition(client, seeded_pa):
    resp = await client.put(
        f"{BASE}/prior-auth/2001",
        json={
            "effDate": "01/01/2026",
            "termDate": "12/31/2027",
            "drugName": "HUMIRA",
            "ndc": "00074312811",
            "status": "Pending",
        },
        headers=AUTH,
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_missing_pa(client, seeded_pa):
    resp = await client.put(
        f"{BASE}/prior-auth/9999",
        json={
            "effDate": "01/01/2026",
            "termDate": "12/31/2027",
            "drugName": "HUMIRA",
            "ndc": "00074312811",
            "status": "Authorized",
        },
        headers=AUTH,
    )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_notes_only(client, seeded_pa):
    resp = await client.patch(
        f"{BASE}/prior-auth/2001",
        json={"notes": "patched note"},
        headers=AUTH,
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["notes"] == "patched note"
    assert data["status"] == "Authorized"


@pytest.mark.asyncio
async def test_patch_status_to_declined(client, seeded_pa):
    resp = await client.patch(
        f"{BASE}/prior-auth/2003",
        json={"status": "Declined", "reasonCode": "STEP THER"},
        headers=AUTH,
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "Declined"
    assert data["reasonCode"] == "STEP THER"


@pytest.mark.asyncio
async def test_patch_rejects_invalid_transition(client, seeded_pa):
    resp = await client.patch(
        f"{BASE}/prior-auth/2004",
        json={"status": "Expired"},
        headers=AUTH,
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_patch_rejects_expired_pa(client, seeded_pa):
    resp = await client.patch(
        f"{BASE}/prior-auth/2005",
        json={"notes": "x"},
        headers=AUTH,
    )

    assert resp.status_code == 403


# @pytest.mark.asyncio
# async def test_member_prior_auth_list(client, seeded_pa):
#     resp = await client.get(f"{BASE}/members/MBR001/prior-auth", headers=AUTH)
#
#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["pagination"]["total"] == 4
#     assert {row["paId"] for row in body["data"]} == {"2001", "2003", "2004", "2005"}


# @pytest.mark.asyncio
# async def test_member_prior_auth_list_filters_by_status(client, seeded_pa):
#     resp = await client.get(
#         f"{BASE}/members/MBR001/prior-auth?status=Declined", headers=AUTH
#     )
#
#     body = resp.json()
#     assert body["pagination"]["total"] == 1
#     assert body["data"][0]["paId"] == "2004"


# @pytest.mark.asyncio
# async def test_member_prior_auth_list_paginates(client, seeded_pa):
#     resp = await client.get(
#         f"{BASE}/members/MBR001/prior-auth?page=1&pageSize=2", headers=AUTH
#     )
#
#     body = resp.json()
#     assert len(body["data"]) == 2
#     assert body["pagination"]["totalPages"] == 2


@pytest.mark.asyncio
async def test_member_prior_auth_list_unknown_member(client, seeded_pa):
    resp = await client.get(f"{BASE}/members/MBR999/prior-auth", headers=AUTH)

    assert resp.status_code == 404


# @pytest.mark.asyncio
# async def test_member_prior_auth_search(client, seeded_pa):
#     resp = await search(
#         client,
#         {"searchRequest": {"status": "Authorized"}},
#         path="/members/MBR001/prior-auth/search",
#     )
#
#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["pagination"]["total"] == 1
#     assert body["data"][0]["paId"] == "2001"


# @pytest.mark.asyncio
# async def test_member_prior_auth_search_accepts_empty_criteria(client, seeded_pa):
#     resp = await search(
#         client,
#         {"searchRequest": {}},
#         path="/members/MBR001/prior-auth/search",
#     )
#
#     assert resp.status_code == 200
#     assert resp.json()["pagination"]["total"] == 4


@pytest.mark.asyncio
async def test_member_prior_auth_search_unknown_member(client, seeded_pa):
    resp = await search(
        client,
        {"searchRequest": {}},
        path="/members/MBR999/prior-auth/search",
    )

    assert resp.status_code == 404


MEMBER_SEARCH_PATH = "/members/MBR001/prior-auth/search"
EFF = (TODAY - timedelta(days=30)).strftime("%m/%d/%Y")


async def member_search(client, criteria: dict, **envelope):
    return await search(
        client,
        {"searchRequest": criteria, **envelope},
        path=MEMBER_SEARCH_PATH,
    )


@pytest.mark.asyncio
async def test_member_prior_auth_search_by_ndc(client, seeded_pa):
    resp = await member_search(client, {"ndc": "00093721410"})

    assert resp.status_code == 200
    body = resp.json()
    assert {row["paId"] for row in body["data"]} == {"2002"}


@pytest.mark.asyncio
async def test_member_prior_auth_search_by_eff_date_is_exact(client, seeded_pa):
    resp = await member_search(client, {"effDate": EFF})

    body = resp.json()
    assert {row["paId"] for row in body["data"]} == {"2001", "2003", "2004", "2005"}
    assert {row["effDate"] for row in body["data"]} == {EFF}


@pytest.mark.asyncio
async def test_member_prior_auth_search_by_term_date_is_exact(client, seeded_pa):
    resp = await member_search(client, {"termDate": PAST.strftime("%m/%d/%Y")})

    body = resp.json()
    assert body["pagination"]["total"] == 1
    assert body["data"][0]["paId"] == "2005"


@pytest.mark.asyncio
async def test_member_prior_auth_search_combines_criteria(client, seeded_pa):
    resp = await member_search(
        client,
        {
            "ndc": "00074312811",
            "effDate": EFF,
            "termDate": FUTURE.strftime("%m/%d/%Y"),
        },
    )

    body = resp.json()
    assert {row["paId"] for row in body["data"]} == {"2001", "2003", "2004"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field", ["memberId", "paId", "drugName", "provider", "status"]
)
async def test_member_prior_auth_search_ignores_unsupported_criteria(
    client, seeded_pa, field
):
    """Only ndc/effDate/termDate filter; other keys are accepted and dropped."""
    resp = await member_search(client, {field: "nonsense", "ndc": "00093721410"})

    assert resp.status_code == 200
    assert {row["paId"] for row in resp.json()["data"]} == {"2002"}


@pytest.mark.asyncio
@pytest.mark.parametrize("blank", ["", "   ", None])
async def test_member_prior_auth_search_ignores_blank_dates(client, seeded_pa, blank):
    """Empty date boxes must drop the filter, not 422."""
    resp = await member_search(client, {"effDate": blank, "termDate": blank})

    assert resp.status_code == 200
    assert resp.json()["pagination"]["total"] == 5


@pytest.mark.asyncio
async def test_member_prior_auth_search_blank_date_keeps_other_filters(
    client, seeded_pa
):
    resp = await member_search(client, {"ndc": "00093721410", "effDate": ""})

    assert resp.status_code == 200
    assert {row["paId"] for row in resp.json()["data"]} == {"2002"}


@pytest.mark.asyncio
async def test_member_prior_auth_search_rejects_malformed_date(client, seeded_pa):
    resp = await member_search(client, {"effDate": "13/45/2025"})

    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("page_size", [10, 25, 50, 100, 10000])
async def test_member_prior_auth_search_accepts_large_page_sizes(
    client, seeded_pa, page_size
):
    resp = await member_search(
        client, {}, pagination={"page": 1, "pageSize": page_size}
    )

    assert resp.status_code == 200
    assert resp.json()["pagination"]["pageSize"] == page_size


@pytest.mark.asyncio
async def test_member_prior_auth_search_rejects_page_size_above_cap(client, seeded_pa):
    resp = await member_search(client, {}, pagination={"page": 1, "pageSize": 10001})

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_member_prior_auth_search_accepts_full_spec_payload(client, seeded_pa):
    """The PA screen's full payload -- unsupported keys must not 422."""
    resp = await search(
        client,
        {
            "pagination": {"page": 1, "pageSize": 10000},
            "searchRequest": {
                "paId": "1003",
                "memberId": "MBR005",
                "drugName": "LANTUS SOLN 100UNIT/ML",
                "ndc": "00088502005",
                "provider": "DR. SUSAN KIM",
                "effDate": "05/01/2025",
                "termDate": "04/30/2026",
            },
            "sort": {"sortBy": "effDate", "sortDir": "DESC"},
        },
        path=MEMBER_SEARCH_PATH,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"] == []
    assert body["pagination"]["pageSize"] == 10000


@pytest.mark.asyncio
async def test_member_prior_auth_search_sorts_by_eff_date_desc(client, seeded_pa):
    resp = await member_search(
        client, {}, sort={"sortBy": "effDate", "sortDir": "DESC"}
    )

    eff_dates = [row["effDate"] for row in resp.json()["data"]]
    assert eff_dates == sorted(eff_dates, key=_as_date, reverse=True)


def _as_date(value: str) -> date:
    return datetime.strptime(value, "%m/%d/%Y").date()


@pytest.mark.asyncio
async def test_drug_prior_auth_list(client, seeded_pa):
    resp = await client.get(f"{BASE}/drugs/00074312811/prior-auth", headers=AUTH)

    assert resp.status_code == 200
    assert resp.json()["pagination"]["total"] == 4


# @pytest.mark.asyncio
# async def test_drug_prior_auth_list_filters_by_status(client, seeded_pa):
#     resp = await client.get(
#         f"{BASE}/drugs/00074312811/prior-auth?status=Pending", headers=AUTH
#     )
#
#     assert resp.json()["data"][0]["paId"] == "2003"


@pytest.mark.asyncio
async def test_drug_prior_auth_list_unknown_ndc(client, seeded_pa):
    resp = await client.get(f"{BASE}/drugs/11111111111/prior-auth", headers=AUTH)

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_prescriber_prior_auth_list(client, seeded_pa):
    resp = await client.get(f"{BASE}/prescribers/1112223334/prior-auth", headers=AUTH)

    assert resp.status_code == 200
    assert resp.json()["pagination"]["total"] == 5


@pytest.mark.asyncio
async def test_prescriber_prior_auth_list_unknown_npi(client, seeded_pa):
    resp = await client.get(f"{BASE}/prescribers/0000000000/prior-auth", headers=AUTH)

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_prior_auth_endpoints_require_auth(raw_client, seeded_pa):
    resp = await raw_client.get(f"{BASE}/prior-auth/2001")

    assert resp.status_code == 403
