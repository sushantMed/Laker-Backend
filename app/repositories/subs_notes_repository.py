from __future__ import annotations

from sqlalchemy import select

from app.models.subs_notes_model import SubsNotesModel
from app.repositories.base_repository import BaseRepository


class SubsNotesRepository(BaseRepository[SubsNotesModel]):
    model = SubsNotesModel

    async def get_by_subscriber(self, subscriber: str, pc: str) -> list[SubsNotesModel]:
        stmt = (
            select(SubsNotesModel)
            .where(
                SubsNotesModel.subscriber.ilike(subscriber),
                SubsNotesModel.pc.ilike(pc),
            )
            .order_by(SubsNotesModel.linenum.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
