from sqlalchemy import String
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Mapped, mapped_column

from app.core.rbac import resolve_permissions
from app.database.base import Base
from app.database.types import JSONText


class UserModel(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)

    # A user has multiple roles; effective permissions are their union.
    # Stored as JSON text (Oracle has no native array type, and SQLAlchemy's
    # Oracle dialect can't render a native JSON column) with MutableList so
    # in-place mutation (user.roles.append(...)) is tracked and persisted.
    roles: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(JSONText),
        default=lambda: ["readonly"],
        nullable=False,
    )
    session_version: Mapped[int] = mapped_column(default=1, nullable=False)

    @property
    def permission_set(self) -> set[str]:
        return resolve_permissions(self.roles)

    def can(self, perm: str) -> bool:
        return perm in self.permission_set

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
