from __future__ import annotations

from sqlalchemy import select

from app.models.subscob_model import SubscobModel
from app.repositories.base_repository import BaseRepository


class SubscobRepository(BaseRepository[SubscobModel]):
    model = SubscobModel

    async def get_by_subscriber(self, subscriber: str, pc: str) -> list[SubscobModel]:
        stmt = (
            select(SubscobModel)
            .where(
                SubscobModel.subscriber.ilike(subscriber),
                SubscobModel.pc.ilike(pc),
            )
            .order_by(SubscobModel.linenum)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
