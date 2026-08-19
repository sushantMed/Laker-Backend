from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class CardQueueModel(Base):
    """A row of the legacy card print queue (SQLMGR.CARDQ).

    One row per member change that earns a new ID card. The nightly print job
    stamps `printdate` and `batchnum` when the card actually goes out, so a row
    with neither is still queued.
    """

    __tablename__ = "cardq"

    __table_args__ = (
        Index("ix_cardq_subscriber_personcode", "subscriber", "personcode"),
        Index("ix_cardq_timestamp", "timestamp"),
        Index("ix_cardq_batchnum", "batchnum"),
    )

    key: Mapped[Decimal] = mapped_column(
        Numeric, unique=True, index=True, nullable=False
    )
    subscriber: Mapped[str | None] = mapped_column(String(45), nullable=True)
    personcode: Mapped[str | None] = mapped_column(String(2), nullable=True)
    tablename: Mapped[str | None] = mapped_column(String(30), nullable=True)
    fieldname: Mapped[str | None] = mapped_column(String(30), nullable=True)
    oldvalue: Mapped[str | None] = mapped_column(String(100), nullable=True)
    newvalue: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Oracle DATE, but this one carries a time component -- it is the "Change
    # Date" the history grid shows.
    timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    printdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    batchnum: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    reportstatus: Mapped[str | None] = mapped_column(String(7), nullable=True)
