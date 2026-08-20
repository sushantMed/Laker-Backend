from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import SubsSubgroupNotFoundException
from app.models.subs_subgroups_model import SubsSubgroupsModel
from app.schemas.subs_subgroups_schema import SubsSubgroupInfo
from app.services.subs_subgroups_service import SubsSubgroupsService


def make_subgroup(
    subscriber: str = "MBR001",
    pc: str = "01",
    linenum: int = 1,
    subgroup: str | None = "SUBGRP1",
) -> SubsSubgroupsModel:
    return SubsSubgroupsModel(
        subscriber=subscriber, pc=pc, linenum=linenum, subgroup=subgroup
    )


@pytest.fixture
def service() -> SubsSubgroupsService:
    svc = SubsSubgroupsService(session=AsyncMock())
    svc._repo = AsyncMock()
    return svc


async def test_list_subgroups_returns_mapped_info(service: SubsSubgroupsService):
    service._repo.get_by_subscriber.return_value = [make_subgroup()]

    result = await service.list_subgroups("MBR001", "01")

    assert len(result) == 1
    info = result[0]
    assert isinstance(info, SubsSubgroupInfo)
    assert info.subscribernum == "MBR001"
    assert info.pc == "01"
    assert info.subgroup == "SUBGRP1"
    service._repo.get_by_subscriber.assert_awaited_once_with("MBR001", "01")


async def test_list_subgroups_raises_when_empty(service: SubsSubgroupsService):
    service._repo.get_by_subscriber.return_value = []

    with pytest.raises(SubsSubgroupNotFoundException):
        await service.list_subgroups("MBR001", "01")
