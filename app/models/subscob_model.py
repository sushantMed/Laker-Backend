from datetime import date

from sqlalchemy import Date, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import LookupBase


class SubscobModel(LookupBase):
    __tablename__ = "SUBSCOB"

    subscriber: Mapped[str] = mapped_column("SUBSCRIBER", String(45), primary_key=True)
    pc: Mapped[str] = mapped_column("PC", String(2), primary_key=True)
    linenum: Mapped[int] = mapped_column("LINENUM", Numeric, primary_key=True)

    ocflag: Mapped[str | None] = mapped_column("OCFLAG", String(1))
    startdt: Mapped[date | None] = mapped_column("STARTDT", Date)
    enddt: Mapped[date | None] = mapped_column("ENDDT", Date)
    covnote: Mapped[str | None] = mapped_column("COVNOTE", String(100))
    primaryinsuranceid: Mapped[str | None] = mapped_column(
        "PRIMARYINSURANCEID", String(18)
    )
    bin: Mapped[str | None] = mapped_column("BIN", String(6))
    pcn: Mapped[str | None] = mapped_column("PCN", String(10))
    groupnum: Mapped[str | None] = mapped_column("GROUPNUM", String(15))
    payor: Mapped[str | None] = mapped_column("PAYOR", String(40))
    otherid: Mapped[str | None] = mapped_column("OTHERID", String(18))
    lastchanged: Mapped[date | None] = mapped_column("LASTCHANGED", Date)

    def __repr__(self) -> str:
        return (
            f"<SubscobModel subscriber={self.subscriber!r} pc={self.pc!r} "
            f"linenum={self.linenum}>"
        )
