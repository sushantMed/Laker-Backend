from __future__ import annotations

from sqlalchemy import select

from app.models.groups_model import GroupsModel
from app.repositories.base_repository import BaseRepository


class GroupsRepository(BaseRepository[GroupsModel]):
    model = GroupsModel

    async def get_by_groupnum(self, groupnum: str) -> GroupsModel | None:
        stmt = select(GroupsModel).where(GroupsModel.groupnum.ilike(groupnum))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
