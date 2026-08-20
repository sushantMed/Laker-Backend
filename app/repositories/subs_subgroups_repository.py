from __future__ import annotations

from sqlalchemy import select

from app.models.subs_subgroups_model import SubsSubgroupsModel
from app.repositories.base_repository import BaseRepository


class SubsSubgroupsRepository(BaseRepository[SubsSubgroupsModel]):
    model = SubsSubgroupsModel

    async def get_by_subscriber(
        self, subscriber: str, pc: str
    ) -> list[SubsSubgroupsModel]:
        stmt = (
            select(SubsSubgroupsModel)
            .where(
                SubsSubgroupsModel.subscriber.ilike(subscriber),
                SubsSubgroupsModel.pc.ilike(pc),
            )
            .order_by(SubsSubgroupsModel.linenum)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
