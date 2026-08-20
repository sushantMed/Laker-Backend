from __future__ import annotations

from datetime import date

from sqlalchemy import or_, select

from app.models.subscriber_elig_list_model import SubscriberEligListModel
from app.repositories.base_repository import BaseRepository


class SubscriberEligListRepository(BaseRepository[SubscriberEligListModel]):
    model = SubscriberEligListModel

    async def get_by_subscriber(
        self, subscriber: str, personcode: str, clientcode: str
    ) -> list[SubscriberEligListModel]:
        stmt = (
            select(SubscriberEligListModel)
            .where(
                SubscriberEligListModel.subscriber.ilike(subscriber),
                SubscriberEligListModel.personcode.ilike(personcode),
                SubscriberEligListModel.clientcode.ilike(clientcode),
            )
            .order_by(SubscriberEligListModel.linenum)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_active_eligibility(
        self, subscriber: str, personcode: str, clientcode: str, as_of_date: date
    ) -> list[SubscriberEligListModel]:
        stmt = (
            select(SubscriberEligListModel)
            .where(
                SubscriberEligListModel.subscriber.ilike(subscriber),
                SubscriberEligListModel.personcode.ilike(personcode),
                SubscriberEligListModel.clientcode.ilike(clientcode),
                or_(
                    SubscriberEligListModel.startdt.is_(None),
                    SubscriberEligListModel.startdt <= as_of_date,
                ),
                or_(
                    SubscriberEligListModel.enddt.is_(None),
                    SubscriberEligListModel.enddt >= as_of_date,
                ),
            )
            .order_by(SubscriberEligListModel.linenum)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
