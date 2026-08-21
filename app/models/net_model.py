from datetime import date

from sqlalchemy import Date, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import LookupBase


class NetModel(LookupBase):
    """Maps to the externally managed SQLMGR.NET table.

    Composite primary key (NETNAME, CLIENT). NETNUM carries a separate
    UNIQUE constraint (not the PK) and is what NETLIST.NETNUM references.
    """

    __tablename__ = "net"

    net_name: Mapped[str] = mapped_column("NETNAME", String(30), primary_key=True)
    client: Mapped[str] = mapped_column("CLIENT", String(10), primary_key=True)
    net_num: Mapped[float | None] = mapped_column(
        "NETNUM", Numeric, unique=True, nullable=True
    )
    date_changed: Mapped[date | None] = mapped_column(
        "DATECHANGED", Date, nullable=True
    )
    net_description: Mapped[str | None] = mapped_column(
        "NETDESCRIPTION", String(500), nullable=True
    )
    net_pm: Mapped[str | None] = mapped_column("NETPM", String(50), nullable=True)
    pharm_net_category: Mapped[str | None] = mapped_column(
        "PHARMNETCATEGORY", String(20), nullable=True
    )
    process_control_number: Mapped[str | None] = mapped_column(
        "PROCESSCONTROLNUMBER", String(10), nullable=True
    )
    restrict_type: Mapped[str | None] = mapped_column(
        "RESTRICTTYPE", String(1), nullable=True
    )
    restrict_value: Mapped[str | None] = mapped_column(
        "RESTRICTVALUE", String(20), nullable=True
    )
    open_time: Mapped[str | None] = mapped_column("OPENTIME", String(4), nullable=True)
    close_time: Mapped[str | None] = mapped_column(
        "CLOSETIME", String(4), nullable=True
    )
    bit_flags: Mapped[float | None] = mapped_column("BITFLAGS", Numeric, nullable=True)
    net_type: Mapped[str | None] = mapped_column("NETTYPE", String(3), nullable=True)
    final_compare_yn: Mapped[str | None] = mapped_column(
        "FINAL_COMPARE_YN", String(1), nullable=True
    )
