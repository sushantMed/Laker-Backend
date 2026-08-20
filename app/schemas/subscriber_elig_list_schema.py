from __future__ import annotations

from datetime import date

from pydantic import Field

from app.core.base_model import AppBaseModel as BaseModel

_CAMEL = {"populate_by_name": True, "from_attributes": True}


class SubscriberEligibilityInfo(BaseModel):
    model_config = _CAMEL

    subscriber: str
    personcode: str = Field(alias="personCode")
    clientcode: str = Field(alias="clientCode")
    linenum: int = Field(alias="lineNum")
    startdt: date | None = Field(default=None, alias="startDate")
    enddt: date | None = Field(default=None, alias="endDate")
    changedt: date | None = Field(default=None, alias="changeDate")


class SubscriberEligibilityLookupRequest(BaseModel):
    model_config = _CAMEL

    subscriber: str
    personcode: str = Field(alias="personCode")
    clientcode: str = Field(alias="clientCode")
    as_of_date: date | None = Field(default=None, alias="asOfDate")
