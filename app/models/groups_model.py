from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import LookupBase


class GroupsModel(LookupBase):
    __tablename__ = "GROUPS"

    groupnum: Mapped[str] = mapped_column("GROUPNUM", String(20), primary_key=True)
    bitflags2: Mapped[int | None] = mapped_column("BITFLAGS2", Numeric)

    def __repr__(self) -> str:
        return f"<GroupsModel groupnum={self.groupnum!r} bitflags2={self.bitflags2!r}>"
