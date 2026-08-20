from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import SubscobNotFoundException
from app.models.subscob_model import SubscobModel
from app.schemas.subscob_schema import SubscobInfo
from app.services.subscob_service import SubscobService


def make_subscob(
    subscriber: str = "MBR001",
    pc: str = "01",
    linenum: int = 1,
    ocflag: str | None = "Y",
    covnote: str | None = None,
    primaryinsuranceid: str | None = None,
) -> SubscobModel:
    return SubscobModel(
        subscriber=subscriber,
        pc=pc,
        linenum=linenum,
        ocflag=ocflag,
        covnote=covnote,
        primaryinsuranceid=primaryinsuranceid,
    )


@pytest.fixture
def service() -> SubscobService:
    svc = SubscobService(session=AsyncMock())
    svc._repo = AsyncMock()
    return svc


async def test_list_other_coverage_returns_mapped_info(service: SubscobService):
    service._repo.get_by_subscriber.return_value = [
        make_subscob(covnote="Has other insurance", primaryinsuranceid="INS999")
    ]

    result = await service.list_other_coverage("MBR001", "01")

    assert len(result) == 1
    info = result[0]
    assert isinstance(info, SubscobInfo)
    assert info.subscribernum == "MBR001"
    assert info.pc == "01"
    assert info.ocflag == "Y"
    assert info.covnote == "Has other insurance"
    assert info.primaryinsuranceid == "INS999"
    service._repo.get_by_subscriber.assert_awaited_once_with("MBR001", "01")


async def test_list_other_coverage_raises_when_empty(service: SubscobService):
    service._repo.get_by_subscriber.return_value = []

    with pytest.raises(SubscobNotFoundException):
        await service.list_other_coverage("MBR001", "01")
