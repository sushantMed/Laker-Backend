from sqlalchemy.orm import DeclarativeBase
import uuid
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from uuid import UUID


class Base(DeclarativeBase):
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

