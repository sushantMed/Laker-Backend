from datetime import date

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import LookupBase

# Imported for its side effect of registering the SUBSNOTESTYPE table on
# LookupBase's shared metadata -- required for the SUBSNOTESTYPEID foreign
# key below to resolve, regardless of what else has been imported first.
from app.models.subs_notes_type_model import SubsNotesTypeModel  # noqa: F401


class SubsNotesModel(LookupBase):
    """Maps to the externally managed SQLMGR.SUBSNOTES table.

    Composite primary key (SUBSCRIBER, PC, LINENUM). SUBSNOTESTYPEID is a
    foreign key to SQLMGR.SUBSNOTESTYPE(SUBSNOTESTYPEID).
    """

    __tablename__ = "SUBSNOTES"

    subscriber: Mapped[str] = mapped_column("SUBSCRIBER", String(45), primary_key=True)
    pc: Mapped[str] = mapped_column("PC", String(2), primary_key=True)
    linenum: Mapped[float] = mapped_column("LINENUM", Numeric, primary_key=True)
    timestamp: Mapped[date | None] = mapped_column("TIMESTAMP", Date, nullable=True)
    dt: Mapped[date | None] = mapped_column("DT", Date, nullable=True)
    name: Mapped[str | None] = mapped_column("NAME", String(30), nullable=True)
    note: Mapped[str | None] = mapped_column("NOTE", String(4000), nullable=True)
    source: Mapped[str | None] = mapped_column("SOURCE", String(15), nullable=True)
    subsnotestypeid: Mapped[float | None] = mapped_column(
        "SUBSNOTESTYPEID",
        Numeric,
        ForeignKey("SUBSNOTESTYPE.SUBSNOTESTYPEID"),
        nullable=True,
    )
    alerttitle: Mapped[str | None] = mapped_column(
        "ALERTTITLE", String(100), nullable=True
    )
    alertmessage: Mapped[str | None] = mapped_column(
        "ALERTMESSAGE", String(1000), nullable=True
    )
    alertstartdate: Mapped[date | None] = mapped_column(
        "ALERTSTARTDATE", Date, nullable=True
    )
    alertenddate: Mapped[date | None] = mapped_column(
        "ALERTENDDATE", Date, nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<SubsNotesModel subscriber={self.subscriber!r} pc={self.pc!r} "
            f"linenum={self.linenum}>"
        )
