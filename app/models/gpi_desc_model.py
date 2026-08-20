from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.master_drug_model import MasterDrugModel


class GpiDescModel(Base):
    """Generic name for a full 14-character GPI (legacy GpiDesc).

    Looked up as GPI = '{gpi}'. Partial GPIs are described by GpiListModel
    instead -- see PriorAuthService._load_drug_names.

    NOTE: the legacy DDL for this table was not supplied; the two columns the
    lookup needs are mirrored at MASTERDRUG's widths (gpi 14, gpigenname 60).
    Adjust here and in the migration once the real definition is to hand.
    """

    __tablename__ = "gpidesc"

    gpi: Mapped[str] = mapped_column(
        String(14), unique=True, index=True, nullable=False
    )
    gpigenname: Mapped[str | None] = mapped_column(String(60), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    # Joined on the GPI value, not a foreign key: the two tables load from
    # separate vendor feeds, so a drug can arrive before its GPI is described
    # (and the other way round). A real constraint would reject those loads.
    drugs: Mapped[list[MasterDrugModel]] = relationship(
        "MasterDrugModel",
        primaryjoin="foreign(MasterDrugModel.gpi) == GpiDescModel.gpi",
        viewonly=True,
        lazy="noload",
    )
