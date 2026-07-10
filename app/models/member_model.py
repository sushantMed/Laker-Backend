from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    String,
    func,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.utils.enums import CoverageType, Gender


class MemberModel(Base):
    __tablename__ = "members"

    # ── Primary key ──────────────────────────────────────────────────────────
    member_id: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )

    # ── Family linkage ───────────────────────────────────────────────────────
    # NULL means this member IS the subscriber (cardholder).
    subscriber_member_id: Mapped[str | None] = mapped_column(
        String(20),
        ForeignKey("members.member_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    # ── Name ─────────────────────────────────────────────────────────────────
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    mi: Mapped[str | None] = mapped_column(String(1), nullable=True)

    # ── Demographics ─────────────────────────────────────────────────────────
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[Gender | None] = mapped_column(SQLEnum(Gender), nullable=True)
    ssn: Mapped[str | None] = mapped_column(
        String(11), nullable=True
    )  # stored encrypted in prod

    # ── Contact ──────────────────────────────────────────────────────────────
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language_preference: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # ── Identifiers ──────────────────────────────────────────────────────────
    insured_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    person_code: Mapped[str] = mapped_column(String(5), nullable=False)
    family_position: Mapped[str | None] = mapped_column(String(5), nullable=True)
    rel_code: Mapped[str] = mapped_column(
        String(5), nullable=False
    )  # "01" / "02" / "03+"
    laker_pc: Mapped[str | None] = mapped_column(String(20), nullable=True)
    prev_card_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    cov_type: Mapped[CoverageType | None] = mapped_column(
        SQLEnum(CoverageType), nullable=True
    )

    # ── Eligibility (stored on Member, not a separate table) ─────────────────
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    # ── Plan FK ──────────────────────────────────────────────────────────────
    plan_id: Mapped[str | None] = mapped_column(
        String(20),
        ForeignKey("plans.plan_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    # ── Audit ────────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    plan: Mapped["PlanModel | None"] = relationship(  # noqa: F821
        "PlanModel", back_populates="members", lazy="joined"
    )
    address: Mapped["MemberAddressModel | None"] = relationship(  # noqa: F821
        "MemberAddressModel",
        back_populates="member",
        uselist=False,
        lazy="joined",
        cascade="all, delete-orphan",
    )
    # Self-referential: dependents of this cardholder
    dependents: Mapped[list["MemberModel"]] = relationship(
        "MemberModel",
        foreign_keys=[subscriber_member_id],
        back_populates="subscriber",
        lazy="noload",
    )
    subscriber: Mapped["MemberModel | None"] = relationship(
        "MemberModel",
        foreign_keys=[subscriber_member_id],
        back_populates="dependents",
        remote_side=[member_id],
        lazy="noload",
    )
