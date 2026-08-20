from datetime import date

from sqlalchemy import Date, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import LookupBase


class SubscriberEligListModel(LookupBase):
    __tablename__ = "SUBSCRIBERELIGLIST"

    subscriber: Mapped[str] = mapped_column("SUBSCRIBER", String(45), primary_key=True)
    personcode: Mapped[str] = mapped_column("PERSONCODE", String(2), primary_key=True)
    clientcode: Mapped[str] = mapped_column("CLIENTCODE", String(10), primary_key=True)
    linenum: Mapped[int] = mapped_column("LINENUM", Numeric, primary_key=True)

    startdt: Mapped[date | None] = mapped_column("STARTDT", Date)
    enddt: Mapped[date | None] = mapped_column("ENDDT", Date)
    changedt: Mapped[date | None] = mapped_column("CHANGEDT", Date)

    def __repr__(self) -> str:
        return (
            f"<SubscriberEligListModel subscriber={self.subscriber!r} "
            f"personcode={self.personcode!r} clientcode={self.clientcode!r} "
            f"linenum={self.linenum}>"
        )
