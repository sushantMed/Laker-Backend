from datetime import date

from sqlalchemy import Date, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import LookupBase


class SubscriberGroupListModel(LookupBase):
    __tablename__ = "SUBSCRIBERGROUPLIST"

    subscriber: Mapped[str] = mapped_column("SUBSCRIBER", String(45), primary_key=True)
    clientcode: Mapped[str] = mapped_column("CLIENTCODE", String(10), primary_key=True)
    linenum: Mapped[int] = mapped_column("LINENUM", Numeric, primary_key=True)

    groupnum: Mapped[str | None] = mapped_column("GROUPNUM", String(20), index=True)
    priority: Mapped[int | None] = mapped_column("PRIORITY", Numeric)
    startdt: Mapped[date | None] = mapped_column("STARTDT", Date)
    enddt: Mapped[date | None] = mapped_column("ENDDT", Date)
    covtype: Mapped[str | None] = mapped_column("COVTYPE", String(10))
    changedt: Mapped[date | None] = mapped_column("CHANGEDT", Date)

    def __repr__(self) -> str:
        return (
            f"<SubscriberGroupListModel subscriber={self.subscriber!r} "
            f"clientcode={self.clientcode!r} linenum={self.linenum} "
            f"groupnum={self.groupnum!r}>"
        )
