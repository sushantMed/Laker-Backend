from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from uuid import uuid4, UUID


class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    token: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    family_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class RevokedAccessTokenModel(Base):
    __tablename__ = "revoked_access_tokens"

    token_hash: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
