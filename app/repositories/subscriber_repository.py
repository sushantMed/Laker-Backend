from __future__ import annotations

from sqlalchemy import select

from app.models.member_model import Subscriber
from app.repositories.base_repository import BaseRepository


class SubscriberRepository(BaseRepository[Subscriber]):
    model = Subscriber

    async def get_by_subscriber_and_person(
        self, subscribernum: str, personcode: str
    ) -> Subscriber | None:
        """The cardholder, without needing to know their client code.

        SUBSCRIBER keys on (subscribernum, personcode, clientcode), so one pair
        can carry a row per client. Any of them proves the pair exists, which is
        all the PA search asks.
        """
        stmt = select(Subscriber).where(
            Subscriber.subscribernum.ilike(subscribernum),
            Subscriber.personcode.ilike(personcode),
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

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
