import uuid
from uuid import UUID

from sqlalchemy import Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class LookupBase(DeclarativeBase):
    """Declarative base for externally managed lookup tables.

    These tables share the application's metadata for Alembic, but do not
    inherit the UUID primary key used by application-owned tables.
    """

    metadata = Base.metadata
