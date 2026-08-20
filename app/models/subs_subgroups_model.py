from datetime import date

from sqlalchemy import Date, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import LookupBase


class SubsSubgroupsModel(LookupBase):
    __tablename__ = "SUBSSUBGROUPS"

    # The real SQLMGR DDL declares no primary key on this table. SUBSCRIBER +
    # PC + LINENUM + SUBGROUP is used here as the ORM's mapped composite key
    # (the natural key), mirroring how SUBSCOB/SUBSCRIBERELIGLIST are keyed --
    # it is not enforced as a DB constraint, matching the source DDL exactly.
    subscriber: Mapped[str] = mapped_column("SUBSCRIBER", String(45), primary_key=True)
    pc: Mapped[str] = mapped_column("PC", String(2), primary_key=True)
    linenum: Mapped[int] = mapped_column("LINENUM", Numeric, primary_key=True)
    subgroup: Mapped[str] = mapped_column("SUBGROUP", String(20), primary_key=True)

    startdt: Mapped[date | None] = mapped_column("STARTDT", Date)
    enddt: Mapped[date | None] = mapped_column("ENDDT", Date)
    lastchanged: Mapped[date | None] = mapped_column("LASTCHANGED", Date)

    def __repr__(self) -> str:
        return (
            f"<SubsSubgroupsModel subscriber={self.subscriber!r} pc={self.pc!r} "
            f"linenum={self.linenum} subgroup={self.subgroup!r}>"
        )
