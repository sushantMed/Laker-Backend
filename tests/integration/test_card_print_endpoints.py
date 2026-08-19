from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_queue_model import CardQueueModel
from app.models.member_model import MemberModel
from app.models.plan_model import PlanModel
from app.models.upd_tran_model import UpdTranDetailModel, UpdTranModel
from tests.integration.conftest import AUTH

BASE = "/api/v1"
HISTORY = "/members/MBR001/card-print-history"


def make_card(key: int, **overrides) -> CardQueueModel:
    values = {
        "id": uuid.uuid4(),
        "key": Decimal(key),
        "subscriber": "INS001",
        "personcode": "01",
        "tablename": "MEMBER",
        "fieldname": "LASTNAME",
        "oldvalue": "MARTIN",
        "newvalue": "MARTINEZ",
        "timestamp": datetime(2025, 3, 10, 9, 30, 0),
        "printdate": date(2025, 3, 12),
        "batchnum": Decimal(4501),
        "reportstatus": None,
    }
    values.update(overrides)
    return CardQueueModel(**values)


@pytest_asyncio.fixture()
async def seeded_cards(db_session: AsyncSession):
    db_session.add(
        PlanModel(
            plan_id="PLN001",
            carrier="BlueCross",
            group_name="Acme",
            group_number="GRP001",
        )
    )
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
            # Same subscriber, different person code -- must not leak into MBR001's
            # history.
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
        ]
    )
    db_session.add_all(
        [
            make_card(1001),
            make_card(
                1002,
                timestamp=datetime(2025, 6, 1, 14, 0, 0),
                printdate=date(2025, 6, 3),
                batchnum=Decimal(4780),
            ),
            # Still queued: no print date, no batch.
            make_card(
                1003,
                timestamp=datetime(2025, 9, 20, 8, 15, 0),
                printdate=None,
                batchnum=None,
            ),
            # Cancelled before it printed.
            make_card(
                1004,
                timestamp=datetime(2025, 10, 1, 11, 45, 0),
                printdate=None,
                batchnum=None,
                reportstatus="CANCEL",
            ),
            # Belongs to the dependent, not MBR001.
            make_card(1005, personcode="02"),
            # Different subscriber entirely.
            make_card(1006, subscriber="INS999", personcode="01"),
        ]
    )
    await db_session.flush()


# ── GET listing ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_history_is_scoped_to_subscriber_and_person_code(client, seeded_cards):
    resp = await client.get(f"{BASE}{HISTORY}", headers=AUTH)

    assert resp.status_code == 200
    body = resp.json()
    assert body["pagination"]["total"] == 4
    assert {row["cardQueueKey"] for row in body["data"]} == {
        "1001",
        "1002",
        "1003",
        "1004",
    }


@pytest.mark.asyncio
async def test_history_returns_grid_columns_newest_first(client, seeded_cards):
    resp = await client.get(f"{BASE}{HISTORY}", headers=AUTH)

    rows = resp.json()["data"]
    assert [row["cardQueueKey"] for row in rows] == ["1004", "1003", "1002", "1001"]

    printed = rows[-1]
    assert printed["changeDate"] == "03/10/2025 09:30:00"
    assert printed["printDate"] == "03/12/2025"
    assert printed["batchNum"] == 4501
    assert printed["cardCancelled"] is False


@pytest.mark.asyncio
async def test_history_flags_cancelled_rows(client, seeded_cards):
    resp = await client.get(f"{BASE}{HISTORY}", headers=AUTH)

    cancelled = next(r for r in resp.json()["data"] if r["cardQueueKey"] == "1004")
    assert cancelled["cardCancelled"] is True
    assert cancelled["reportStatus"] == "CANCEL"
    assert cancelled["printDate"] is None
    assert cancelled["batchNum"] is None


@pytest.mark.asyncio
async def test_history_paginates(client, seeded_cards):
    resp = await client.get(f"{BASE}{HISTORY}?page=2&pageSize=2", headers=AUTH)

    body = resp.json()
    assert body["pagination"]["total"] == 4
    assert body["pagination"]["hasNext"] is False
    assert [row["cardQueueKey"] for row in body["data"]] == ["1002", "1001"]


@pytest.mark.asyncio
async def test_history_for_unknown_member_is_404(client, seeded_cards):
    resp = await client.get(f"{BASE}/members/NOPE/card-print-history", headers=AUTH)

    assert resp.status_code == 404


# ── POST search ───────────────────────────────────────────────────────────────


async def search(client, body: dict):
    return await client.post(f"{BASE}{HISTORY}/search", json=body, headers=AUTH)


@pytest.mark.asyncio
async def test_search_with_empty_criteria_returns_full_history(client, seeded_cards):
    resp = await search(client, {"searchRequest": {}})

    assert resp.status_code == 200
    assert resp.json()["pagination"]["total"] == 4


@pytest.mark.asyncio
async def test_search_filters_by_change_date_range(client, seeded_cards):
    resp = await search(
        client,
        {
            "searchRequest": {
                "changeDateFrom": "06/01/2025",
                "changeDateTo": "09/20/2025",
            }
        },
    )

    body = resp.json()
    assert {row["cardQueueKey"] for row in body["data"]} == {"1002", "1003"}


@pytest.mark.asyncio
async def test_search_filters_by_batch_num(client, seeded_cards):
    resp = await search(client, {"searchRequest": {"batchNum": 4780}})

    body = resp.json()
    assert body["pagination"]["total"] == 1
    assert body["data"][0]["cardQueueKey"] == "1002"


@pytest.mark.asyncio
async def test_search_filters_by_cancelled_flag(client, seeded_cards):
    cancelled = await search(client, {"searchRequest": {"cardCancelled": True}})
    active = await search(client, {"searchRequest": {"cardCancelled": False}})

    assert [r["cardQueueKey"] for r in cancelled.json()["data"]] == ["1004"]
    assert {r["cardQueueKey"] for r in active.json()["data"]} == {
        "1001",
        "1002",
        "1003",
    }


@pytest.mark.asyncio
async def test_search_sorts_by_requested_column(client, seeded_cards):
    resp = await search(
        client,
        {"searchRequest": {}, "sort": {"sortBy": "changeDate", "sortDir": "ASC"}},
    )

    assert [r["cardQueueKey"] for r in resp.json()["data"]] == [
        "1001",
        "1002",
        "1003",
        "1004",
    ]


@pytest.mark.asyncio
async def test_search_rejects_inverted_date_range(client, seeded_cards):
    resp = await search(
        client,
        {
            "searchRequest": {
                "changeDateFrom": "09/20/2025",
                "changeDateTo": "06/01/2025",
            }
        },
    )

    assert resp.status_code == 422


# ── Cancel ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cancel_marks_row_cancelled(client, seeded_cards):
    resp = await client.post(f"{BASE}{HISTORY}/1003/cancel", headers=AUTH)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["cardQueueKey"] == "1003"
    assert data["cardCancelled"] is True
    assert data["reportStatus"] == "CANCEL"


@pytest.mark.asyncio
async def test_cancel_writes_audit_trail(client, seeded_cards, db_session):
    await client.post(f"{BASE}{HISTORY}/1003/cancel", headers=AUTH)

    header = (await db_session.execute(select(UpdTranModel))).scalars().one()
    assert header.screenkey == "INS00101"
    assert header.userid == "tester@example."  # clipped to USERID's 15 chars

    detail = (await db_session.execute(select(UpdTranDetailModel))).scalars().one()
    assert detail.trankey == header.trankey
    assert detail.linenum == 1
    assert detail.updtable == "CARDQ"
    assert detail.detailkey == "1003"
    assert detail.fieldname == "REPORTSTATUS"
    assert detail.oldvalue is None
    assert detail.newvalue == "CANCEL"


@pytest.mark.asyncio
async def test_cancel_rejects_already_printed_row(client, seeded_cards):
    resp = await client.post(f"{BASE}{HISTORY}/1001/cancel", headers=AUTH)

    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_cancel_rejects_already_cancelled_row(client, seeded_cards):
    resp = await client.post(f"{BASE}{HISTORY}/1004/cancel", headers=AUTH)

    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_cancel_rejects_row_belonging_to_another_member(client, seeded_cards):
    resp = await client.post(f"{BASE}{HISTORY}/1005/cancel", headers=AUTH)

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cancel_rejects_unknown_key(client, seeded_cards):
    resp = await client.post(f"{BASE}{HISTORY}/not-a-number/cancel", headers=AUTH)

    assert resp.status_code == 404
