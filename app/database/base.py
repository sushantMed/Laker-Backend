from sqlalchemy.orm import DeclarativeBase
import uuid
from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from uuid import UUID


class Base(DeclarativeBase):
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

