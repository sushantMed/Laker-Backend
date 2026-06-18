from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.database.base import Base
from uuid import uuid4, UUID

from app.models.member_model import MemberModel
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

class MemberAddressModel(Base):
    __tablename__ = "member_addresses"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    member_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("members.member_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # 1-to-1 with Member
        index=True,
    )

    address1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    zip: Mapped[str | None] = mapped_column(String(10), nullable=True)

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

    member: Mapped["MemberModel"] = relationship(  # noqa: F821
        "MemberModel", back_populates="address"
    )
