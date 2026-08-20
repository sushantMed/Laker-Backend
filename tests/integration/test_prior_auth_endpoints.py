from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.drug_model import DrugModel
from app.models.gpi_desc_model import GpiDescModel
from app.models.gpi_list_model import GpiListModel
from app.models.master_drug_model import MasterDrugModel
from app.models.member_model import MemberModel, Subscriber
from app.models.plan_model import PlanModel
from app.models.prescriber_model import PrescriberModel
from app.models.prior_auth_model import PriorAuthModel
from app.utils.enums import BrandGeneric, Maintenance
from tests.integration.conftest import AUTH

BASE = "/api/v1"

# The PA screen ships one route: POST /prior-auth/search.
# Every other PA route is commented out in app/api/v1/prior_auth.py, so the
# tests covering them would only assert that an unmounted path 404s. Re-enable
# the route and drop this marker from its tests together.
ROUTE_DISABLED = pytest.mark.skip(
    reason="route commented out in app/api/v1/prior_auth.py"
)

TODAY = date.today()
FUTURE = TODAY + timedelta(days=200)
PAST = TODAY - timedelta(days=200)
EARLIER = TODAY - timedelta(days=45)


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


def make_subscriber(subscribernum: str, personcode: str, **overrides) -> Subscriber:
    values = {
        "subscribernum": subscribernum,
        "personcode": personcode,
        "clientcode": "CLI001",
        "lastname": "MARTINEZ",
        "firstname": "CARLOS",
        "status": "A",
    }
    values.update(overrides)
    return Subscriber(**values)


@pytest_asyncio.fixture()
async def seeded_pa(db_session: AsyncSession, seeded_lookups):
    # The PA search proves the cardholder against SUBSCRIBER, not members.
    db_session.add_all(
        [
            make_subscriber("INS001", "01"),
            make_subscriber("INS001", "02", firstname="SOFIA"),
            make_subscriber("INS003", "01", firstname="MINH", lastname="NGUYEN"),
        ]
    )

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
                # Below the EFF floor the eff-date tests key, so it filters in
                # and out on demand.
                effdate=EARLIER,
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
@ROUTE_DISABLED
async def test_search_by_ndc(client, seeded_pa):
    resp = await search(client, {"searchRequest": {"ndc": "00074312811"}})

    assert resp.status_code == 200
    body = resp.json()
    assert body["pagination"]["total"] == 4
    assert {row["ndc"] for row in body["data"]} == {"00074312811"}


@pytest.mark.asyncio
@ROUTE_DISABLED
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
@ROUTE_DISABLED
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
@ROUTE_DISABLED
async def test_search_by_drug_name_matches_catalogue(client, seeded_pa):
    resp = await search(client, {"searchRequest": {"drugName": "humira"}})

    assert resp.json()["pagination"]["total"] == 4


@pytest.mark.asyncio
@ROUTE_DISABLED
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
@ROUTE_DISABLED
async def test_search_without_criteria_is_rejected(client, seeded_pa):
    resp = await search(client, {"searchRequest": {}})

    assert resp.status_code == 400


@pytest.mark.asyncio
@ROUTE_DISABLED
async def test_search_with_reversed_date_range_is_rejected(client, seeded_pa):
    resp = await search(
        client,
        {"searchRequest": {"effDateFrom": "12/31/2026", "effDateTo": "01/01/2026"}},
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
@ROUTE_DISABLED
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
@ROUTE_DISABLED
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
@ROUTE_DISABLED
async def test_search_returns_empty_page_when_nothing_matches(client, seeded_pa):
    resp = await search(client, {"searchRequest": {"ndc": "99999999999"}})

    assert resp.status_code == 200
    assert resp.json()["data"] == []


@pytest.mark.asyncio
@ROUTE_DISABLED
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
@ROUTE_DISABLED
async def test_family_pa_resolves_to_lowest_person_code(client, seeded_pa):
    resp = await client.get(f"{BASE}/prior-auth/2006", headers=AUTH)

    data = resp.json()["data"]
    assert data["personCodes"] == "01,02"
    assert data["memberId"] == "MBR003"


@pytest.mark.asyncio
@ROUTE_DISABLED
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
@ROUTE_DISABLED
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
@ROUTE_DISABLED
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
@ROUTE_DISABLED
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
@ROUTE_DISABLED
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
@ROUTE_DISABLED
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
@ROUTE_DISABLED
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
@ROUTE_DISABLED
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
@ROUTE_DISABLED
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
@ROUTE_DISABLED
async def test_patch_rejects_invalid_transition(client, seeded_pa):
    resp = await client.patch(
        f"{BASE}/prior-auth/2004",
        json={"status": "Expired"},
        headers=AUTH,
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
@ROUTE_DISABLED
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
@pytest.mark.parametrize(
    "cardholder",
    [
        {"subscriberNum": "INS999", "personCodes": "01"},
        {"subscriberNum": "INS001", "personCodes": "99"},
    ],
)
async def test_member_prior_auth_search_unknown_subscriber(
    client, seeded_pa, cardholder
):
    """Both keys are checked against SUBSCRIBER; either one wrong is a 404."""
    resp = await search(
        client, {"searchRequest": cardholder}, path="/prior-auth/search"
    )

    assert resp.status_code == 404
    # The handler renders AppException.message, not its code.
    assert "not found" in resp.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_member_prior_auth_search_requires_the_cardholder_keys(client, seeded_pa):
    resp = await search(client, {"searchRequest": {}}, path="/prior-auth/search")

    assert resp.status_code == 422


MEMBER_SEARCH_PATH = "/prior-auth/search"
EFF = (TODAY - timedelta(days=30)).strftime("%m/%d/%Y")


async def member_search(client, criteria: dict, **envelope):
    """The subscriber search, defaulting to the cardholder the PAs hang off."""
    criteria = {"subscriberNum": "INS001", "personCodes": "01", **criteria}
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
    assert {row["authNum"] for row in body["data"]} == {"2002"}


@pytest.mark.asyncio
@pytest.mark.parametrize("keyed", ["093721410", "0093721410", "00093721410"])
async def test_member_prior_auth_search_pads_short_ndc(client, seeded_pa, keyed):
    """A 9- or 10-char NDC still finds the 11-char row it belongs to."""
    resp = await member_search(client, {"ndc": keyed})

    assert resp.status_code == 200
    assert {row["authNum"] for row in resp.json()["data"]} == {"2002"}


@pytest.mark.asyncio
@pytest.mark.parametrize("keyed", ["93721410", "000937214100"])
async def test_member_prior_auth_search_rejects_out_of_range_ndc(
    client, seeded_pa, keyed
):
    resp = await member_search(client, {"ndc": keyed})

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_member_prior_auth_search_row_returns_pa_columns(client, seeded_pa):
    """The member grid gets the PA's own columns -- no member/drug resolution."""
    resp = await member_search(client, {"ndc": "00093721410"})

    row = resp.json()["data"][0]
    assert row == {
        "authNum": "2002",
        "ndc": "00093721410",
        "gpi": "39400010100310",
        "drugNameNdc": "ATORVASTATIN CALCIUM",
        "drugNameGpi": "ATORVASTATIN CALCIUM",
        "action": "A",
        "effDate": EARLIER.strftime("%m/%d/%Y"),
        "termDate": FUTURE.strftime("%m/%d/%Y"),
        "lastUser": None,
        "subscriberNum": "INS001",
        "personCodes": "02",
    }


@pytest.mark.asyncio
async def test_member_prior_auth_search_row_names_a_manual_drug(client, seeded_pa):
    """With no NDC on the PA, only the GPI-side name is filled in."""
    resp = await member_search(client, {"subscriberNum": "INS003", "personCodes": "01"})

    row = resp.json()["data"][0]
    assert row["authNum"] == "2006"
    assert row["ndc"] is None
    assert row["drugNameNdc"] is None
    assert row["drugNameGpi"] == "COMPOUNDED CREAM"
    assert row["personCodes"] == "01,02"


@pytest.mark.asyncio
async def test_member_prior_auth_search_by_eff_date_is_a_lower_bound(client, seeded_pa):
    """effDate is a floor: PAs starting on or after it come back."""
    resp = await member_search(client, {"effDate": EFF})

    body = resp.json()
    assert {row["authNum"] for row in body["data"]} == {"2001", "2003", "2004", "2005"}
    assert {row["effDate"] for row in body["data"]} == {EFF}


@pytest.mark.asyncio
async def test_member_prior_auth_search_eff_date_drops_earlier_pas(client, seeded_pa):
    resp = await member_search(
        client, {"effDate": (TODAY - timedelta(days=29)).strftime("%m/%d/%Y")}
    )

    assert resp.json()["pagination"]["total"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("keyed", ["past", "future"])
async def test_member_prior_auth_search_accepts_but_ignores_term_date(
    client, seeded_pa, keyed
):
    """termDate is accepted and dropped.

    PriorAuthService.search_prior_auths_for_subscriber no longer passes it to the
    repository, so a ceiling that would once have left only the ended PA now
    changes nothing. Restore the kwarg and this test goes back to asserting a
    ceiling.
    """
    ceiling = PAST if keyed == "past" else FUTURE
    resp = await member_search(client, {"termDate": ceiling.strftime("%m/%d/%Y")})

    body = resp.json()
    assert {row["authNum"] for row in body["data"]} == {
        "2001",
        "2002",
        "2003",
        "2004",
        "2005",
    }


@pytest.mark.asyncio
async def test_member_prior_auth_search_combines_criteria(client, seeded_pa):
    """ndc and effDate AND together; the termDate in the payload is dropped."""
    resp = await member_search(
        client,
        {
            "ndc": "00074312811",
            "effDate": EFF,
            "termDate": FUTURE.strftime("%m/%d/%Y"),
        },
    )

    body = resp.json()
    assert {row["authNum"] for row in body["data"]} == {"2001", "2003", "2004", "2005"}


@pytest.mark.asyncio
async def test_member_prior_auth_search_term_date_does_not_narrow_the_result(
    client, seeded_pa
):
    """The same criteria with the ceiling flipped return the same rows."""
    payload = {"ndc": "00074312811", "effDate": EFF}

    with_past = await member_search(
        client, {**payload, "termDate": PAST.strftime("%m/%d/%Y")}
    )
    with_future = await member_search(
        client, {**payload, "termDate": FUTURE.strftime("%m/%d/%Y")}
    )

    expected = {"2001", "2003", "2004", "2005"}
    assert {row["authNum"] for row in with_past.json()["data"]} == expected
    assert {row["authNum"] for row in with_future.json()["data"]} == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field", ["memberId", "paId", "drugName", "provider", "status"]
)
async def test_member_prior_auth_search_ignores_unsupported_criteria(
    client, seeded_pa, field
):
    """Only ndc/effDate filter; other keys are accepted and dropped."""
    resp = await member_search(client, {field: "nonsense", "ndc": "00093721410"})

    assert resp.status_code == 200
    assert {row["authNum"] for row in resp.json()["data"]} == {"2002"}


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
    assert {row["authNum"] for row in resp.json()["data"]} == {"2002"}


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
                "subscriberNum": "INS001",
                "personCodes": "01",
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


# ── effDateFrom / effDateTo ───────────────────────────────────────────────────

OLDER = TODAY - timedelta(days=120)


def _fmt(value: date) -> str:
    return value.strftime("%m/%d/%Y")


@pytest_asyncio.fixture()
async def seeded_old_pa(db_session: AsyncSession, seeded_pa):
    """Adds 2010 at 120 days back -- the seeded PAs sit at 30 and 45."""
    db_session.add(make_pa(2010, effdate=OLDER))
    await db_session.flush()


@pytest.mark.asyncio
async def test_member_prior_auth_search_unbounded_returns_full_history(
    client, seeded_old_pa
):
    """Neither bound keyed means the member's whole history."""
    resp = await member_search(client, {})

    assert {row["authNum"] for row in resp.json()["data"]} == {
        "2001",
        "2002",
        "2003",
        "2004",
        "2005",
        "2010",
    }


@pytest.mark.asyncio
async def test_member_prior_auth_search_eff_date_from_is_a_floor(client, seeded_old_pa):
    resp = await member_search(
        client, {"effDateFrom": _fmt(TODAY - timedelta(days=90))}
    )

    assert "2010" not in {row["authNum"] for row in resp.json()["data"]}


@pytest.mark.asyncio
async def test_member_prior_auth_search_eff_date_to_is_a_ceiling(client, seeded_old_pa):
    """Only the oldest PA sits at or below a ceiling 90 days back."""
    resp = await member_search(client, {"effDateTo": _fmt(TODAY - timedelta(days=90))})

    assert {row["authNum"] for row in resp.json()["data"]} == {"2010"}


@pytest.mark.asyncio
async def test_member_prior_auth_search_eff_date_range_brackets_the_result(
    client, seeded_old_pa
):
    """2002 sits at 45 days back, alone inside a 40-to-50-day bracket."""
    resp = await member_search(
        client,
        {
            "effDateFrom": _fmt(TODAY - timedelta(days=50)),
            "effDateTo": _fmt(TODAY - timedelta(days=40)),
        },
    )

    assert {row["authNum"] for row in resp.json()["data"]} == {"2002"}


@pytest.mark.asyncio
@pytest.mark.parametrize("bound", ["effDateFrom", "effDateTo"])
async def test_member_prior_auth_search_eff_date_bounds_are_inclusive(
    client, seeded_old_pa, bound
):
    """A PA effective exactly on either bound is inside it."""
    resp = await member_search(client, {bound: _fmt(OLDER)})

    assert "2010" in {row["authNum"] for row in resp.json()["data"]}


@pytest.mark.asyncio
async def test_member_prior_auth_search_rejects_reversed_eff_date_range(
    client, seeded_pa
):
    resp = await member_search(
        client, {"effDateFrom": _fmt(TODAY), "effDateTo": _fmt(OLDER)}
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("blank", ["", "   ", None])
async def test_member_prior_auth_search_ignores_blank_eff_date_bounds(
    client, seeded_old_pa, blank
):
    resp = await member_search(client, {"effDateFrom": blank, "effDateTo": blank})

    assert resp.status_code == 200
    assert resp.json()["pagination"]["total"] == 6


@pytest.mark.asyncio
async def test_member_prior_auth_search_eff_date_still_floors(client, seeded_old_pa):
    """effDate is the older name for the floor and keeps working."""
    resp = await member_search(client, {"effDate": _fmt(TODAY - timedelta(days=90))})

    assert "2010" not in {row["authNum"] for row in resp.json()["data"]}


@pytest.mark.asyncio
async def test_member_prior_auth_search_eff_date_and_from_both_apply(
    client, seeded_old_pa
):
    """Two floors AND together, so the later of the two is what bites."""
    resp = await member_search(
        client,
        {
            "effDate": _fmt(OLDER),
            "effDateFrom": _fmt(TODAY - timedelta(days=40)),
        },
    )

    # 2002 sits at 45 days back, below the tighter floor; 2010 at 120.
    auths = {row["authNum"] for row in resp.json()["data"]}
    assert "2002" not in auths
    assert "2010" not in auths


@pytest.mark.asyncio
@pytest.mark.parametrize("keyed", [" INS001", "INS001 ", "  INS001  "])
async def test_member_prior_auth_search_trims_subscriber_num(client, seeded_pa, keyed):
    """A subscriber number keyed with surrounding spaces still resolves."""
    resp = await member_search(client, {"subscriberNum": keyed})

    assert resp.status_code == 200
    assert resp.json()["pagination"]["total"] == 5


@pytest.mark.asyncio
async def test_member_prior_auth_search_trims_person_codes(client, seeded_pa):
    resp = await member_search(client, {"personCodes": " 01 "})

    assert resp.status_code == 200
    assert resp.json()["pagination"]["total"] == 5


# ── Drug names from the reference tables ──────────────────────────────────────


def make_master_drug(ndc: str, *, gpi: str, gen_name: str, description: str):
    return MasterDrugModel(
        ndcupchri=ndc, gpi=gpi, gpigenname=gen_name, proddescabbrev=description
    )


@pytest_asyncio.fixture()
async def seeded_drug_reference(db_session: AsyncSession, seeded_pa):
    db_session.add_all(
        [
            # PA 2001's full NDC -- named by its product description.
            make_master_drug(
                "00074312811",
                gpi="27250030100120",
                gen_name="ADALIMUMAB",
                description="HUMIRA PEN 40MG",
            ),
            # Prefix 000937214 covers three packages. Two share a GPI, so that
            # pair's generic name wins the count.
            make_master_drug(
                "00093721410",
                gpi="39400010100310",
                gen_name="ATORVASTATIN CALCIUM",
                description="ATORVASTATIN 10MG",
            ),
            make_master_drug(
                "00093721430",
                gpi="39400010100310",
                gen_name="ATORVASTATIN CALCIUM",
                description="ATORVASTATIN 30MG",
            ),
            make_master_drug(
                "00093721490",
                gpi="39400010100999",
                gen_name="ATORVASTATIN/EZETIMIBE",
                description="ATORVASTATIN COMBO",
            ),
            GpiDescModel(gpi="27250030100120", gpigenname="ADALIMUMAB (FULL GPI)"),
            GpiListModel(gpi="G3940", name="ANTIHYPERLIPIDEMICS"),
        ]
    )
    db_session.add_all(
        [
            make_pa(2007, ndc="000937214", gpi="3940", genname=None),
            make_pa(2008, ndc=None, gpi="COMPOUND", genname="NOT A DRUG NAME"),
        ]
    )
    await db_session.flush()


def _row(resp, auth_num: str) -> dict:
    return next(row for row in resp.json()["data"] if row["authNum"] == auth_num)


@pytest.mark.asyncio
async def test_member_search_names_a_full_ndc_from_masterdrug(
    client, seeded_drug_reference
):
    """An 11-character NDC takes MASTERDRUG's product description."""
    row = _row(await member_search(client, {}), "2001")

    assert row["drugNameNdc"] == "HUMIRA PEN 40MG"


@pytest.mark.asyncio
async def test_member_search_names_a_short_ndc_by_commonest_gpi(
    client, seeded_drug_reference
):
    """A 9-character NDC takes the generic name most rows under it carry."""
    row = _row(await member_search(client, {}), "2007")

    assert row["drugNameNdc"] == "ATORVASTATIN CALCIUM"


@pytest.mark.asyncio
async def test_member_search_names_a_full_gpi_from_gpidesc(
    client, seeded_drug_reference
):
    row = _row(await member_search(client, {}), "2001")

    assert row["drugNameGpi"] == "ADALIMUMAB (FULL GPI)"


@pytest.mark.asyncio
async def test_member_search_names_a_partial_gpi_from_gpilist(
    client, seeded_drug_reference
):
    """A partial GPI is keyed in GpiList with a leading G."""
    row = _row(await member_search(client, {}), "2007")

    assert row["drugNameGpi"] == "ANTIHYPERLIPIDEMICS"


@pytest.mark.asyncio
async def test_member_search_binds_no_name_to_a_compound_gpi(
    client, seeded_drug_reference
):
    """A compound stands for no one drug, so its GPI names nothing."""
    row = _row(await member_search(client, {}), "2008")

    assert row["drugNameGpi"] is None


@pytest.mark.asyncio
async def test_member_search_falls_back_to_the_pa_s_own_drug_name(
    client, seeded_drug_reference, db_session: AsyncSession
):
    """An NDC the reference tables don't carry keeps the name on the PA."""
    db_session.add(make_pa(2009, ndc="99999999999", genname="LOCALLY NAMED DRUG"))
    await db_session.flush()

    row = _row(await member_search(client, {}), "2009")

    assert row["drugNameNdc"] == "LOCALLY NAMED DRUG"


@pytest.mark.asyncio
@ROUTE_DISABLED
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
#     assert resp.json()["data"][0]["authNum"] == "2003"


@pytest.mark.asyncio
async def test_drug_prior_auth_list_unknown_ndc(client, seeded_pa):
    resp = await client.get(f"{BASE}/drugs/11111111111/prior-auth", headers=AUTH)

    assert resp.status_code == 404


@pytest.mark.asyncio
@ROUTE_DISABLED
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
    """The one mounted PA route rejects an unauthenticated caller."""
    resp = await raw_client.post(f"{BASE}{MEMBER_SEARCH_PATH}", json={})

    assert resp.status_code == 403
