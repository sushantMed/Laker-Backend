from __future__ import annotations

from datetime import date

from pydantic import Field

from app.core.base_model import AppBaseModel as BaseModel

_CAMEL = {"populate_by_name": True, "from_attributes": True}


class CommentInfo(BaseModel):
    model_config = _CAMEL

    subscriber: str = Field(alias="subscriberNum")
    pc: str
    linenum: float = Field(alias="lineNum")
    name: str | None = Field(default=None, alias="user")
    dt: date | None = Field(default=None, alias="date")
    note: str | None = None
