from sqlalchemy import (
    String,
    Integer,
    Boolean,
    DateTime,
    func,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from app.database.base import Base
from app.utils.enums import BrandGeneric, Maintenance


class DrugModel(Base):
    __tablename__ = "drugs"

    ndc: Mapped[str] = mapped_column(String(11), unique=True, index=True, nullable=False)
    gpi: Mapped[str] = mapped_column(String(14), index=True, nullable=False)
    drug_name: Mapped[str] = mapped_column(String(255), nullable=False)

    brand_generic: Mapped[BrandGeneric] = mapped_column(
        SQLEnum(BrandGeneric), nullable=False
    )
    maintenance: Mapped[Maintenance] = mapped_column(
        SQLEnum(Maintenance), nullable=False
    )

    desi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tier: Mapped[int | None] = mapped_column(Integer, nullable=True)
    formulary_status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    repackage_ind: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

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
