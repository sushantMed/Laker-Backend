from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_queue_model import CardQueueModel

# CARDQ.REPORTSTATUS is 7 characters wide; this is the value the card-cancel
# screen stamps on a queued row. Everything else counts as "not cancelled".
CANCELLED_REPORT_STATUS = "CANCEL"

_SORTABLE_COLUMNS = {
    "cardQueueKey": CardQueueModel.key,
    "key": CardQueueModel.key,
    "changeDate": CardQueueModel.timestamp,
    "printDate": CardQueueModel.printdate,
    "batchNum": CardQueueModel.batchnum,
    "cardCancelled": CardQueueModel.reportstatus,
    "reportStatus": CardQueueModel.reportstatus,
}
_DEFAULT_SORT_COLUMN = CardQueueModel.timestamp

_STATUS = func.upper(func.coalesce(CardQueueModel.reportstatus, ""))


def _cancelled_clause(cancelled: bool):
    if cancelled:
        return _STATUS == CANCELLED_REPORT_STATUS
    return _STATUS != CANCELLED_REPORT_STATUS


class CardRepository:
    """Reads and writes SQLMGR.CARDQ, the legacy ID-card print queue."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_key(self, key: Decimal) -> CardQueueModel | None:
        stmt = select(CardQueueModel).where(CardQueueModel.key == key)
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def search_print_history(
        self,
        *,
        subscriber: str,
        person_code: str | None = None,
        change_date_from: date | None = None,
        change_date_to: date | None = None,
        batch_num: int | None = None,
        cancelled: bool | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str | None = None,
        sort_dir: str = "desc",
    ) -> tuple[Sequence[CardQueueModel], int]:
        stmt = select(CardQueueModel).where(CardQueueModel.subscriber == subscriber)

        if person_code:
            stmt = stmt.where(CardQueueModel.personcode == person_code)
        if change_date_from:
            stmt = stmt.where(
                CardQueueModel.timestamp >= datetime.combine(change_date_from, time.min)
            )
        if change_date_to:
            # CARDQ.TIMESTAMP carries a time, so an inclusive upper bound has to
            # run to the end of the day rather than midnight.
            stmt = stmt.where(
                CardQueueModel.timestamp <= datetime.combine(change_date_to, time.max)
            )
        if batch_num is not None:
            stmt = stmt.where(CardQueueModel.batchnum == batch_num)
        if cancelled is not None:
            stmt = stmt.where(_cancelled_clause(cancelled))

        return await self._paginate(stmt, page, page_size, sort_by, sort_dir)

    async def _paginate(
        self,
        stmt,
        page: int,
        page_size: int,
        sort_by: str | None,
        sort_dir: str,
    ) -> tuple[Sequence[CardQueueModel], int]:
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        sort_column = _SORTABLE_COLUMNS.get(sort_by, _DEFAULT_SORT_COLUMN)
        order_fn = desc if str(sort_dir).lower() == "desc" else asc
        # Tie-break on the primary key so paging stays stable when several rows
        # share a timestamp -- the queue writes them in bursts.
        stmt = stmt.order_by(order_fn(sort_column), desc(CardQueueModel.key))

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(stmt)
        return result.unique().scalars().all(), total


def is_cancelled(card: CardQueueModel) -> bool:
    return (card.reportstatus or "").strip().upper() == CANCELLED_REPORT_STATUS


def is_printed(card: CardQueueModel) -> bool:
    """A row the print job has already picked up can no longer be cancelled."""
    return card.printdate is not None or card.batchnum is not None
