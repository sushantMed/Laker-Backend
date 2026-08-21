from datetime import date

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import LookupBase


class NetListModel(LookupBase):
    """Maps to the externally managed NETLIST table.

    Composite primary key (NETNUM, LINENUM); NETNUM is a foreign key to
    SQLMGR.NET(NETNUM) with ON DELETE CASCADE enforced at the DB level.
    """

    __tablename__ = "netlist"

    net_num: Mapped[float] = mapped_column(
        "NETNUM",
        Numeric,
        ForeignKey("net.NETNUM", ondelete="CASCADE"),
        primary_key=True,
    )
    line_num: Mapped[float] = mapped_column("LINENUM", Numeric, primary_key=True)
    type: Mapped[str | None] = mapped_column("TYPE", String(1), nullable=True)
    value: Mapped[str | None] = mapped_column("VALUE", String(30), nullable=True)
    inc: Mapped[str | None] = mapped_column("INC", String(1), nullable=True)
    start_date: Mapped[date | None] = mapped_column("STARTDT", Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column("ENDDT", Date, nullable=True)
