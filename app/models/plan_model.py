from uuid import UUID, uuid4

from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.database.base import Base
from app.models.member_model import MemberModel  # noqa: F401
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


class PlanModel(Base):
    __tablename__ = "plans"

    # Surrogate PK (internal)
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Business key — used on Member.plan_id FK
    plan_id: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )

    carrier: Mapped[str] = mapped_column(String(100), nullable=False)
    group_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    group_number: Mapped[str | None] = mapped_column(String(20), nullable=True)

    rx_bin: Mapped[str | None] = mapped_column(String(10), nullable=True)
    rx_pcn: Mapped[str | None] = mapped_column(String(20), nullable=True)

    region: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location: Mapped[str | None] = mapped_column(String(50), nullable=True)

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

    # Relationship — back-ref from MemberModel
    members: Mapped[list["MemberModel"]] = relationship(  # noqa: F821
        "MemberModel", back_populates="plan", lazy="noload"
    )
