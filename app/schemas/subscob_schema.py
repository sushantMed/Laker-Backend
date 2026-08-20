from __future__ import annotations

from datetime import date

from pydantic import Field

from app.core.base_model import AppBaseModel as BaseModel

_CAMEL = {"populate_by_name": True, "from_attributes": True}


class SubscobInfo(BaseModel):
    model_config = _CAMEL

    subscribernum: str = Field(alias="subscriberNum")
    pc: str
    linenum: int = Field(alias="lineNum")
    ocflag: str | None = Field(default=None, alias="ocFlag")
    startdt: date | None = Field(default=None, alias="startDate")
    enddt: date | None = Field(default=None, alias="endDate")
    covnote: str | None = Field(default=None, alias="covNote")
    primaryinsuranceid: str | None = Field(default=None, alias="primaryInsuranceId")
