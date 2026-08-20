from __future__ import annotations

from datetime import date

from pydantic import Field

from app.core.base_model import AppBaseModel as BaseModel

_CAMEL = {"populate_by_name": True, "from_attributes": True}


class SubsSubgroupInfo(BaseModel):
    model_config = _CAMEL

    subscribernum: str = Field(alias="subscriberNum")
    pc: str
    linenum: int = Field(alias="lineNum")
    subgroup: str | None = Field(default=None, alias="subGroup")
    startdt: date | None = Field(default=None, alias="startDate")
    enddt: date | None = Field(default=None, alias="endDate")
