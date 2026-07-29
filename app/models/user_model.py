from sqlalchemy import String
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.rbac import grant_map, permissions_from_grants
from app.database.base import Base
from app.database.types import JSONText
from app.models.permission_model import UserPermissionModel


class UserModel(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)

    # Legacy, and no longer consulted: authorization comes from `grants` alone.
    # Still mapped because the column is NOT NULL with no server default, so
    # inserts would fail without it. Nothing should read this.
    roles: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(JSONText),
        default=lambda: [],
        nullable=False,
    )
    session_version: Mapped[int] = mapped_column(default=1, nullable=False)

    # selectin, not lazy: permission_set is a sync property read inside request
    # handlers, where a lazy load would raise MissingGreenlet under asyncio.
    # This way the grants arrive with the user in one extra query.
    grants: Mapped[list[UserPermissionModel]] = relationship(
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    @property
    def _grant_rows(self) -> list[tuple[str, str, str]]:
        return [(g.pername, g.viewperm, g.saveperm) for g in self.grants]

    @property
    def permission_set(self) -> set[str]:
        """Permission codes this user holds. No grants -> no permissions."""
        return permissions_from_grants(self._grant_rows)

    @property
    def grant_map(self) -> dict[str, list[str]]:
        """``{screen: [actions]}`` as returned by /auth/me, screens hyphenated."""
        return grant_map(self._grant_rows)

    def can(self, perm: str) -> bool:
        return perm in self.permission_set

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
