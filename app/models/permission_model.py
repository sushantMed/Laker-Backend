from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class UserPermissionModel(Base):
    """Per-user screen grant, mirroring the legacy ``sql.userperm`` shape.

    One row per screen, with the same ``viewperm``/``saveperm`` flags. Stored as
    CHAR(1) 'Y'/'N' since Oracle has no native boolean.
    """

    __tablename__ = "user_permissions"
    __table_args__ = (
        UniqueConstraint("user_id", "pername", name="uq_userperm_user_pername"),
        CheckConstraint("viewperm IN ('Y','N')", name="ck_userperm_viewperm_yn"),
        CheckConstraint("saveperm IN ('Y','N')", name="ck_userperm_saveperm_yn"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pername: Mapped[str] = mapped_column(String(60), nullable=False)
    viewperm: Mapped[str] = mapped_column(String(1), default="N", nullable=False)
    saveperm: Mapped[str] = mapped_column(String(1), default="N", nullable=False)
