"""SQLAlchemy model for SQLMGR.ZIPCODES (US ZIP code reference/lookup data)."""

from decimal import Decimal

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import LookupBase


class ZipCodeModel(LookupBase):
    """
    Static reference table of US ZIP codes — city, county, state, timezone,
    and lat/long. Read-only lookup data (not written to by application
    logic); used to resolve a ZIP code's centroid coordinates for radius
    searches (e.g. pharmacy lookup) instead of averaging coordinates off of
    whichever target-table rows happen to share the entered ZIP.
    """

    __tablename__ = "ZIPCODES"

    zip: Mapped[str] = mapped_column("ZIP", String(5), primary_key=True)

    city: Mapped[str | None] = mapped_column("CITY", String(45))
    abbreviation: Mapped[str | None] = mapped_column("ABBREVIATION", String(13))
    countyname: Mapped[str | None] = mapped_column("COUNTYNAME", String(40))
    statename: Mapped[str | None] = mapped_column("STATENAME", String(28))
    state: Mapped[str | None] = mapped_column("STATE", String(2))
    citytype: Mapped[str | None] = mapped_column("CITYTYPE", String(1))
    ziptype: Mapped[str | None] = mapped_column("ZIPTYPE", String(1))
    fips: Mapped[Decimal | None] = mapped_column("FIPS", Numeric(5, 0))
    areacode: Mapped[Decimal | None] = mapped_column("AREACODE", Numeric(3, 0))
    overlay: Mapped[str | None] = mapped_column("OVERLAY", String(50))
    timezone: Mapped[str | None] = mapped_column("TIMEZONE", String(2))
    dst: Mapped[str | None] = mapped_column("DST", String(1))
    utc: Mapped[str | None] = mapped_column("UTC", String(15))
    latitude: Mapped[Decimal | None] = mapped_column("LATITUDE", Numeric(12, 7))
    longitude: Mapped[Decimal | None] = mapped_column("LONGITUDE", Numeric(12, 7))

    def __repr__(self) -> str:
        return (
            f"<ZipCodeModel zip={self.zip!r} city={self.city!r} state={self.state!r}>"
        )
