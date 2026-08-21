from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import LookupBase


class SubsNotesTypeModel(LookupBase):
    """Maps to the externally managed SQLMGR.SUBSNOTESTYPE table.

    Simple lookup table: SUBSNOTESTYPEID (PK) -> SUBSNOTESTYPEDESC.
    Referenced by SQLMGR.SUBSNOTES.SUBSNOTESTYPEID.
    """

    __tablename__ = "SUBSNOTESTYPE"

    subsnotestypeid: Mapped[float] = mapped_column(
        "SUBSNOTESTYPEID", Numeric, primary_key=True
    )
    subsnotestypedesc: Mapped[str | None] = mapped_column(
        "SUBSNOTESTYPEDESC", String(35), nullable=True
    )
