from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class GpiListModel(Base):
    """Name for a partial (class-level) GPI (legacy GpiList).

    The key carries a leading "G", so a PA holding GPI "3940" is looked up as
    "G3940" -- the repository adds the prefix, callers pass the bare GPI.

    NOTE: the legacy DDL for this table was not supplied; the two columns the
    lookup needs are sized to hold "G" + a full 14-character GPI, with the name
    at MASTERDRUG's gpigenname width. Adjust here and in the migration once the
    real definition is to hand.
    """

    __tablename__ = "gpilist"

    gpi: Mapped[str] = mapped_column(
        String(15), unique=True, index=True, nullable=False
    )
    name: Mapped[str | None] = mapped_column(String(60), nullable=True)
