from __future__ import annotations

from datetime import date

from sqlalchemy import func, or_, select

from app.models.subscriber_group_list_model import SubscriberGroupListModel
from app.repositories.base_repository import BaseRepository


class SubscriberGroupListRepository(BaseRepository[SubscriberGroupListModel]):
    model = SubscriberGroupListModel

    async def get_max_linenum(self, subscriber: str, clientcode: str) -> int:
        stmt = select(func.max(SubscriberGroupListModel.linenum)).where(
            SubscriberGroupListModel.subscriber.ilike(subscriber),
            SubscriberGroupListModel.clientcode.ilike(clientcode),
        )
        result = await self.session.execute(stmt)
        max_linenum = result.scalar_one_or_none()
        return int(max_linenum) if max_linenum is not None else 0

    async def get_by_line(
        self, subscriber: str, clientcode: str, linenum: int
    ) -> SubscriberGroupListModel | None:
        stmt = select(SubscriberGroupListModel).where(
            SubscriberGroupListModel.subscriber.ilike(subscriber),
            SubscriberGroupListModel.clientcode.ilike(clientcode),
            SubscriberGroupListModel.linenum == linenum,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_subscriber(
        self, subscriber: str, clientcode: str
    ) -> list[SubscriberGroupListModel]:
        stmt = (
            select(SubscriberGroupListModel)
            .where(
                SubscriberGroupListModel.subscriber.ilike(subscriber),
                SubscriberGroupListModel.clientcode.ilike(clientcode),
            )
            # Most recent start date first, per the "Cardholder Eligibility
            # Information" table's sort acceptance criterion.
            .order_by(SubscriberGroupListModel.startdt.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def add(self, group: SubscriberGroupListModel) -> SubscriberGroupListModel:
        self.session.add(group)
        await self.session.flush()
        return group

    async def get_active_groups(
        self, subscriber: str, clientcode: str, as_of_date: date
    ) -> list[SubscriberGroupListModel]:
        stmt = (
            select(SubscriberGroupListModel)
            .where(
                SubscriberGroupListModel.subscriber.ilike(subscriber),
                SubscriberGroupListModel.clientcode.ilike(clientcode),
                or_(
                    SubscriberGroupListModel.startdt.is_(None),
                    SubscriberGroupListModel.startdt <= as_of_date,
                ),
                or_(
                    SubscriberGroupListModel.enddt.is_(None),
                    SubscriberGroupListModel.enddt >= as_of_date,
                ),
            )
            .order_by(SubscriberGroupListModel.startdt.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
