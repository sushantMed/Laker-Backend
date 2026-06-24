from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from app.database.base import Base


class PharmacyModel(Base):
    __tablename__ = "pharmacies"

    nabp: Mapped[str] = mapped_column(String(7), unique=True, index=True, nullable=False)
    npi: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    pharmacy_name: Mapped[str] = mapped_column(String(255), nullable=False)

    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    zip: Mapped[str] = mapped_column(String(10), nullable=False)

    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    fax: Mapped[str | None] = mapped_column(String(20), nullable=True)

    is_24_hour: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    in_network: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

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
