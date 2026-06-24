"""
Claim ORM model.

"""

from __future__ import annotations

from datetime import date

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ClaimModel(Base):
    __tablename__ = "claims"

    __table_args__ = (
        Index(
            "ix_claims_member_id_date_filled_is_test_claim",
            "member_id",
            "date_filled",
            "is_test_claim",
        ),
    )

    # ── Identity ─────────────────────────────────────────────────────────────
    # Primary key (`id`, UUID) is inherited from Base.
    claim_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    auth_num: Mapped[str] = mapped_column(String(20), unique=True, index=True)

    # ── Member linkage ───────────────────────────────────────────────────────
    member_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("members.member_id", ondelete="RESTRICT"),
        index=True,
    )
    member = relationship("MemberModel", lazy="noload")

    # ── Prescription details ─────────────────────────────────────────────────
    rx_number: Mapped[str] = mapped_column(String(20), index=True)
    drug_name: Mapped[str] = mapped_column(String(255))
    ndc: Mapped[str] = mapped_column(String(13), index=True)

    date_filled: Mapped[date] = mapped_column(Date, index=True)
    date_written: Mapped[date | None] = mapped_column(Date, nullable=True)
    quantity: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    days_supply: Mapped[int | None] = mapped_column(Integer, nullable=True)
    refills_remaining: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Pharmacy(NABP) ─────────────────────────────────────────────────────────────
    pharmacy_npi: Mapped[str | None] = mapped_column(String(10), nullable=True)
    pharmacy_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Prescriber ───────────────────────────────────────────────────────────
    prescriber_npi: Mapped[str | None] = mapped_column(String(10), nullable=True)
    prescriber_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Cost ─────────────────────────────────────────────────────────────────
    ingredient_cost: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    dispensing_fee: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    copay: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    total_paid: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    # ── Flags / plan ─────────────────────────────────────────────────────────
    is_test_claim: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    plan_id: Mapped[str | None] = mapped_column(
        String(20),
        ForeignKey("plans.plan_id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Audit ────────────────────────────────────────────────────────────────
    created_at: Mapped[date] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[date] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )