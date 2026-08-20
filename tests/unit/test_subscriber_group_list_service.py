from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import (
    EligibilityDateOverlapException,
    InvalidEligibilityDataException,
    SubscriberGroupNotFoundException,
    SubscriberNotFoundException,
)
from app.models.groups_model import GroupsModel
from app.models.member_model import Subscriber
from app.models.subscriber_group_list_model import SubscriberGroupListModel
from app.schemas.subscriber_group_list_schema import (
    EligibilityCreate,
    EligibilityUpdate,
    SubscriberGroupInfo,
)
from app.services.subscriber_group_list_service import (
    CARDHOLDER_PERSON_CODE,
    DEFAULT_CLIENTCODE,
    SubscriberGroupListService,
)


def make_subscriber(
    subscribernum: str = "MBR001",
    personcode: str = CARDHOLDER_PERSON_CODE,
    clientcode: str = DEFAULT_CLIENTCODE,
) -> Subscriber:
    return Subscriber(
        subscribernum=subscribernum, personcode=personcode, clientcode=clientcode
    )


def make_group_row(
    subscriber: str = "MBR001",
    clientcode: str = DEFAULT_CLIENTCODE,
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


@pytest.fixture
def service() -> SubscriberGroupListService:
    svc = SubscriberGroupListService(session=AsyncMock())
    svc._repo = AsyncMock()
    svc._subscriber_repo = AsyncMock()
    svc._groups_repo = AsyncMock()
    return svc


# ── list_eligibility ─────────────────────────────────────────────────────────


async def test_list_eligibility_returns_mapped_info(
    service: SubscriberGroupListService,
):
    service._subscriber_repo.get_by_subscribernum.return_value = make_subscriber()
    service._repo.get_by_subscriber.return_value = [make_group_row()]

    result = await service.list_eligibility("MBR001")

    assert len(result) == 1
    info = result[0]
    assert isinstance(info, SubscriberGroupInfo)
    assert info.subscribernum == "MBR001"
    assert info.linenum == 1
    assert info.groupnum == "MLB09ARMS"
    assert info.covtype == "I"
    service._subscriber_repo.get_by_subscribernum.assert_awaited_once_with(
        "MBR001", CARDHOLDER_PERSON_CODE, DEFAULT_CLIENTCODE
    )
    service._repo.get_by_subscriber.assert_awaited_once_with(
        "MBR001", DEFAULT_CLIENTCODE
    )


async def test_list_eligibility_raises_when_subscriber_missing(
    service: SubscriberGroupListService,
):
    service._subscriber_repo.get_by_subscribernum.return_value = None

    with pytest.raises(SubscriberNotFoundException):
        await service.list_eligibility("NOPE")

    service._repo.get_by_subscriber.assert_not_called()


# ── add_eligibility ──────────────────────────────────────────────────────────


async def test_add_eligibility_creates_row_with_next_linenum(
    service: SubscriberGroupListService,
):
    service._subscriber_repo.get_by_subscribernum.return_value = make_subscriber()
    service._groups_repo.get_by_groupnum.return_value = None
    service._repo.get_by_subscriber.return_value = []
    service._repo.get_max_linenum.return_value = 3
    request = EligibilityCreate(
        groupNum="GRP999",
        startDate=date(2027, 1, 1),
        endDate=date(2027, 12, 31),
        coverageType="F",
    )

    result = await service.add_eligibility("MBR001", request)

    added = service._repo.add.await_args.args[0]
    assert added.subscriber == "MBR001"
    assert added.clientcode == DEFAULT_CLIENTCODE
    assert added.linenum == 4
    assert added.covtype == "F"
    service._session.commit.assert_awaited_once()
    service._session.refresh.assert_awaited_once()
    assert result.linenum == 4
    assert result.groupnum == "GRP999"


async def test_add_eligibility_raises_when_subscriber_missing(
    service: SubscriberGroupListService,
):
    service._subscriber_repo.get_by_subscribernum.return_value = None
    request = EligibilityCreate(groupNum="GRP1", startDate=date(2027, 1, 1))

    with pytest.raises(SubscriberNotFoundException):
        await service.add_eligibility("NOPE", request)

    service._repo.add.assert_not_called()


async def test_add_eligibility_raises_on_date_overlap(
    service: SubscriberGroupListService,
):
    service._subscriber_repo.get_by_subscribernum.return_value = make_subscriber()
    service._groups_repo.get_by_groupnum.return_value = None
    service._repo.get_by_subscriber.return_value = [make_group_row()]
    request = EligibilityCreate(
        groupNum="GRP999", startDate=date(2023, 1, 1), endDate=date(2023, 6, 1)
    )

    with pytest.raises(EligibilityDateOverlapException):
        await service.add_eligibility("MBR001", request)

    service._repo.add.assert_not_called()


async def test_add_eligibility_forces_cardholder_only_covtype(
    service: SubscriberGroupListService,
):
    service._subscriber_repo.get_by_subscribernum.return_value = make_subscriber()
    service._groups_repo.get_by_groupnum.return_value = GroupsModel(
        groupnum="GRP999", bitflags2=512
    )
    service._repo.get_by_subscriber.return_value = []
    service._repo.get_max_linenum.return_value = 0
    request = EligibilityCreate(groupNum="GRP999", startDate=date(2027, 1, 1))

    result = await service.add_eligibility("MBR001", request)

    assert result.covtype == "I"


async def test_add_eligibility_rejects_conflicting_covtype_for_cardholder_only_group(
    service: SubscriberGroupListService,
):
    service._subscriber_repo.get_by_subscribernum.return_value = make_subscriber()
    service._groups_repo.get_by_groupnum.return_value = GroupsModel(
        groupnum="GRP999", bitflags2=512
    )
    request = EligibilityCreate(
        groupNum="GRP999", startDate=date(2027, 1, 1), coverageType="F"
    )

    with pytest.raises(InvalidEligibilityDataException):
        await service.add_eligibility("MBR001", request)

    service._repo.add.assert_not_called()


# ── update_eligibility ───────────────────────────────────────────────────────


async def test_update_eligibility_updates_existing_row(
    service: SubscriberGroupListService,
):
    existing = make_group_row()
    service._subscriber_repo.get_by_subscribernum.return_value = make_subscriber()
    service._repo.get_by_line.return_value = existing
    service._groups_repo.get_by_groupnum.return_value = None
    service._repo.get_by_subscriber.return_value = [existing]
    request = EligibilityUpdate(
        groupNum="MLB09ARMS",
        startDate=date(2022, 1, 1),
        endDate=date(2027, 12, 31),
        coverageType="F",
    )

    result = await service.update_eligibility("MBR001", 1, request)

    assert result.enddt == date(2027, 12, 31)
    assert result.covtype == "F"
    service._session.commit.assert_awaited_once()


async def test_update_eligibility_raises_when_line_not_found(
    service: SubscriberGroupListService,
):
    service._subscriber_repo.get_by_subscribernum.return_value = make_subscriber()
    service._repo.get_by_line.return_value = None
    request = EligibilityUpdate(groupNum="MLB09ARMS", startDate=date(2022, 1, 1))

    with pytest.raises(SubscriberGroupNotFoundException):
        await service.update_eligibility("MBR001", 999, request)


async def test_update_eligibility_raises_when_subscriber_missing(
    service: SubscriberGroupListService,
):
    service._subscriber_repo.get_by_subscribernum.return_value = None
    request = EligibilityUpdate(groupNum="MLB09ARMS", startDate=date(2022, 1, 1))

    with pytest.raises(SubscriberNotFoundException):
        await service.update_eligibility("NOPE", 1, request)

    service._repo.get_by_line.assert_not_called()
