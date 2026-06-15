from sqlalchemy import String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.database.base import Base


class MemberAddressModel(Base):
    __tablename__ = "member_addresses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    member_id: Mapped[str] = mapped_column(
        String(20),
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
