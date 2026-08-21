from __future__ import annotations

from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.member_model import Subscriber
from app.models.subs_notes_model import SubsNotesModel
from app.models.subs_subgroups_model import SubsSubgroupsModel
from app.models.subscob_model import SubscobModel
from app.models.subscriber_group_list_model import SubscriberGroupListModel
from tests.integration.conftest import AUTH

BASE = "/api/v1/members"
CLIENTCODE = "YYY"


def make_subscriber(
    subscribernum: str = "MBR001", personcode: str = "01", clientcode: str = CLIENTCODE
) -> Subscriber:
    return Subscriber(
        subscribernum=subscribernum, personcode=personcode, clientcode=clientcode
    )


def make_group_row(
    subscriber: str = "MBR001",
    clientcode: str = CLIENTCODE,
    linenum: int = 1,
    groupnum: str = "MLB09ARMS",
    startdt: date = date(2022, 1, 1),
    enddt: date | None = date(2026, 12, 31),
    covtype: str | None = "I",
) -> SubscriberGroupListModel:
    return SubscriberGroupListModel(
        subscriber=subscriber,
        clientcode=clientcode,
        linenum=linenum,
        groupnum=groupnum,
        priority=linenum,
        startdt=startdt,
        enddt=enddt,
        covtype=covtype,
        changedt=date.today(),
    )


@pytest_asyncio.fixture()
async def seeded_subscriber(db_session: AsyncSession):
    db_session.add_all([make_subscriber(), make_group_row()])
    await db_session.flush()


# ── group-eligibility ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_group_eligibility_success(client, seeded_subscriber):
    resp = await client.get(
        f"{BASE}/group-eligibility", params={"subscribernum": "MBR001"}, headers=AUTH
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["subscriberNum"] == "MBR001"
    assert data[0]["groupNum"] == "MLB09ARMS"
    assert data[0]["coverageType"] == "I"
    assert "clientCode" not in data[0]
    assert "subscriber" not in data[0]


@pytest.mark.asyncio
async def test_list_group_eligibility_case_insensitive(client, seeded_subscriber):
    resp = await client.get(
        f"{BASE}/group-eligibility", params={"subscribernum": "mbr001"}, headers=AUTH
    )

    assert resp.status_code == 200
    assert resp.json()["data"][0]["subscriberNum"] == "MBR001"


@pytest.mark.asyncio
async def test_list_group_eligibility_unknown_subscriber(client):
    resp = await client.get(
        f"{BASE}/group-eligibility", params={"subscribernum": "NOPE"}, headers=AUTH
    )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_group_eligibility_requires_query_param(client):
    resp = await client.get(f"{BASE}/group-eligibility", headers=AUTH)

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_group_eligibility_requires_auth(raw_client, seeded_subscriber):
    resp = await raw_client.get(
        f"{BASE}/group-eligibility", params={"subscribernum": "MBR001"}
    )

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_add_group_eligibility_success(client, seeded_subscriber):
    resp = await client.post(
        f"{BASE}/group-eligibility",
        params={"subscribernum": "MBR001"},
        json={
            "groupNum": "GRP999",
            "startDate": "2027-01-01",
            "endDate": "2027-12-31",
            "coverageType": "F",
        },
        headers=AUTH,
    )

    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["groupNum"] == "GRP999"
    assert data["lineNum"] == 2


@pytest.mark.asyncio
async def test_add_group_eligibility_overlap_conflict(client, seeded_subscriber):
    resp = await client.post(
        f"{BASE}/group-eligibility",
        params={"subscribernum": "MBR001"},
        json={
            "groupNum": "GRP999",
            "startDate": "2023-01-01",
            "endDate": "2023-06-01",
        },
        headers=AUTH,
    )

    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_add_group_eligibility_end_before_start(client, seeded_subscriber):
    resp = await client.post(
        f"{BASE}/group-eligibility",
        params={"subscribernum": "MBR001"},
        json={
            "groupNum": "GRP999",
            "startDate": "2027-01-01",
            "endDate": "2026-01-01",
        },
        headers=AUTH,
    )

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_add_group_eligibility_unknown_subscriber(client):
    resp = await client.post(
        f"{BASE}/group-eligibility",
        params={"subscribernum": "NOPE"},
        json={"groupNum": "GRP1", "startDate": "2027-01-01"},
        headers=AUTH,
    )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_group_eligibility_success(client, seeded_subscriber):
    resp = await client.put(
        f"{BASE}/group-eligibility/1",
        params={"subscribernum": "MBR001"},
        json={
            "groupNum": "MLB09ARMS",
            "startDate": "2022-01-01",
            "endDate": "2027-12-31",
            "coverageType": "F",
        },
        headers=AUTH,
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    # AppBaseModel serializes date fields as MM/DD/YYYY, not ISO.
    assert data["endDate"] == "12/31/2027"
    assert data["coverageType"] == "F"


@pytest.mark.asyncio
async def test_update_group_eligibility_line_not_found(client, seeded_subscriber):
    resp = await client.put(
        f"{BASE}/group-eligibility/999",
        params={"subscribernum": "MBR001"},
        json={"groupNum": "MLB09ARMS", "startDate": "2022-01-01"},
        headers=AUTH,
    )

    assert resp.status_code == 404


# ── cob ──────────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture()
async def seeded_cob(db_session: AsyncSession, seeded_subscriber):
    db_session.add(
        SubscobModel(
            subscriber="MBR001",
            pc="01",
            linenum=1,
            ocflag="Y",
            covnote="Has other insurance",
            primaryinsuranceid="INS999",
        )
    )
    await db_session.flush()


@pytest.mark.asyncio
async def test_list_cob_success(client, seeded_cob):
    resp = await client.get(
        f"{BASE}/cob",
        params={"subscribernum": "MBR001", "personcode": "01"},
        headers=AUTH,
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data[0]["subscriberNum"] == "MBR001"
    assert data[0]["ocFlag"] == "Y"
    assert data[0]["primaryInsuranceId"] == "INS999"
    assert "bin" not in data[0]
    assert "payor" not in data[0]


@pytest.mark.asyncio
async def test_list_cob_not_found(client):
    resp = await client.get(
        f"{BASE}/cob",
        params={"subscribernum": "MBR001", "personcode": "01"},
        headers=AUTH,
    )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_cob_requires_personcode(client):
    resp = await client.get(
        f"{BASE}/cob", params={"subscribernum": "MBR001"}, headers=AUTH
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_cob_requires_auth(raw_client, seeded_cob):
    resp = await raw_client.get(
        f"{BASE}/cob", params={"subscribernum": "MBR001", "personcode": "01"}
    )

    assert resp.status_code == 403


# ── subgroups ────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture()
async def seeded_subgroup(db_session: AsyncSession, seeded_subscriber):
    db_session.add(
        SubsSubgroupsModel(subscriber="MBR001", pc="01", linenum=1, subgroup="SUBGRP1")
    )
    await db_session.flush()


@pytest.mark.asyncio
async def test_list_subgroups_success(client, seeded_subgroup):
    resp = await client.get(
        f"{BASE}/subgroups",
        params={"subscribernum": "MBR001", "personcode": "01"},
        headers=AUTH,
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data[0]["subscriberNum"] == "MBR001"
    assert data[0]["subGroup"] == "SUBGRP1"


@pytest.mark.asyncio
async def test_list_subgroups_not_found(client):
    resp = await client.get(
        f"{BASE}/subgroups",
        params={"subscribernum": "MBR001", "personcode": "01"},
        headers=AUTH,
    )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_subgroups_requires_auth(raw_client, seeded_subgroup):
    resp = await raw_client.get(
        f"{BASE}/subgroups", params={"subscribernum": "MBR001", "personcode": "01"}
    )

    assert resp.status_code == 403


# ── comments ─────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture()
async def seeded_comments(db_session: AsyncSession, seeded_subscriber):
    db_session.add_all(
        [
            SubsNotesModel(
                subscriber="MBR001",
                pc="01",
                linenum=1,
                dt=date(2026, 1, 1),
                name="alice",
                note="First note",
            ),
            SubsNotesModel(
                subscriber="MBR001",
                pc="01",
                linenum=2,
                dt=date(2026, 2, 1),
                name="bob",
                note="Second note",
            ),
        ]
    )
    await db_session.flush()


@pytest.mark.asyncio
async def test_list_comments_success(client, seeded_comments):
    resp = await client.get(
        f"{BASE}/comments",
        params={"subscribernum": "MBR001", "personcode": "01"},
        headers=AUTH,
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 2
    # Newest (highest linenum) first.
    assert data[0]["note"] == "Second note"
    assert data[0]["user"] == "bob"
    assert data[1]["note"] == "First note"


@pytest.mark.asyncio
async def test_list_comments_empty_returns_empty_list(client):
    """Unlike cob/subgroups, no comments yet is a normal state, not a 404."""
    resp = await client.get(
        f"{BASE}/comments",
        params={"subscribernum": "MBR001", "personcode": "01"},
        headers=AUTH,
    )

    assert resp.status_code == 200
    assert resp.json()["data"] == []


@pytest.mark.asyncio
async def test_list_comments_requires_personcode(client):
    resp = await client.get(
        f"{BASE}/comments", params={"subscribernum": "MBR001"}, headers=AUTH
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_comments_requires_auth(raw_client, seeded_comments):
    resp = await raw_client.get(
        f"{BASE}/comments", params={"subscribernum": "MBR001", "personcode": "01"}
    )

    assert resp.status_code == 403
