from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class UpdTranModel(Base):
    """Header of a legacy audit transaction (SQLMGR.UPDTRAN).

    Every screen that writes to a base table logs one header row plus one
    detail row per changed field.
    """

    __tablename__ = "updtran"

    __table_args__ = (
        # A real UNIQUE constraint, not just a unique index: Oracle will not
        # accept updtrandetail's foreign key against an index alone (ORA-02270).
        UniqueConstraint("trankey", name="uq_updtran_trankey"),
        Index("ix_updtran_clientcode_screenkey", "clientcode", "screenkey"),
    )

    trankey: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    clientcode: Mapped[str | None] = mapped_column(String(10), nullable=True)
    tranid: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    screenid: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    screenkey: Mapped[str | None] = mapped_column(String(50), nullable=True)
    userid: Mapped[str | None] = mapped_column(String(15), nullable=True)
    trants: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    details: Mapped[list[UpdTranDetailModel]] = relationship(
        "UpdTranDetailModel",
        back_populates="transaction",
        cascade="all, delete-orphan",
        lazy="noload",
    )


class UpdTranDetailModel(Base):
    """One changed field within an audit transaction (SQLMGR.UPDTRANDETAIL)."""

    __tablename__ = "updtrandetail"

    __table_args__ = (
        Index("ix_updtrandetail_trankey_linenum", "trankey", "linenum", unique=True),
        Index("ix_updtrandetail_updtable_detailkey", "updtable", "detailkey"),
    )

    trankey: Mapped[Decimal] = mapped_column(
        Numeric,
        ForeignKey("updtran.trankey", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    linenum: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    detailkey: Mapped[str | None] = mapped_column(String(35), nullable=True)
    updtable: Mapped[str | None] = mapped_column(String(25), nullable=True)
    fieldname: Mapped[str | None] = mapped_column(String(20), nullable=True)
    newvalue: Mapped[str | None] = mapped_column(String(200), nullable=True)
    oldvalue: Mapped[str | None] = mapped_column(String(200), nullable=True)
    txnum: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    seqnum: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)

    transaction: Mapped[UpdTranModel] = relationship(
        "UpdTranModel", back_populates="details", lazy="noload"
    )
