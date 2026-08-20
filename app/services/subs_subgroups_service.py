from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import SubsSubgroupNotFoundException
from app.models.subs_subgroups_model import SubsSubgroupsModel
from app.repositories.subs_subgroups_repository import SubsSubgroupsRepository
from app.schemas.subs_subgroups_schema import SubsSubgroupInfo


class SubsSubgroupsService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = SubsSubgroupsRepository(session)

    def _to_info(self, g: SubsSubgroupsModel) -> SubsSubgroupInfo:
        return SubsSubgroupInfo(
            subscriberNum=g.subscriber,
            pc=g.pc,
            lineNum=g.linenum,
            subGroup=g.subgroup,
            startDate=g.startdt,
            endDate=g.enddt,
        )

    async def list_subgroups(
        self, subscriber: str, personcode: str
    ) -> list[SubsSubgroupInfo]:
        rows = await self._repo.get_by_subscriber(subscriber, personcode)
        if not rows:
            raise SubsSubgroupNotFoundException(
                "No sub-group records found for the given subscriber and person code."
            )
        return [self._to_info(r) for r in rows]
