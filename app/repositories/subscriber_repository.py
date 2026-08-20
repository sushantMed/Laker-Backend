from __future__ import annotations

from sqlalchemy import select

from app.models.member_model import Subscriber
from app.repositories.base_repository import BaseRepository


class SubscriberRepository(BaseRepository[Subscriber]):
    model = Subscriber

    async def get_by_subscribernum(
        self, subscribernum: str, personcode: str, clientcode: str
    ) -> Subscriber | None:
        stmt = select(Subscriber).where(
            Subscriber.subscribernum.ilike(subscribernum),
            Subscriber.personcode.ilike(personcode),
            Subscriber.clientcode.ilike(clientcode),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
