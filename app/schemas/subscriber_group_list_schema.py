from __future__ import annotations

from datetime import date

from pydantic import Field, model_validator

from app.core.base_model import AppBaseModel as BaseModel
from app.core.exceptions import InvalidEligibilityDataException

_CAMEL = {"populate_by_name": True, "from_attributes": True}


class SubscriberGroupInfo(BaseModel):
    model_config = _CAMEL

    subscribernum: str = Field(alias="subscriberNum")
    linenum: int = Field(alias="lineNum")
    groupnum: str | None = Field(default=None, alias="groupNum")
    startdt: date | None = Field(default=None, alias="startDate")
    enddt: date | None = Field(default=None, alias="endDate")
    covtype: str | None = Field(default=None, alias="coverageType")


class SubscriberGroupLookupRequest(BaseModel):
    model_config = _CAMEL

    subscriber: str
    clientcode: str = Field(alias="clientCode")
    as_of_date: date | None = Field(default=None, alias="asOfDate")


class EligibilityCreate(BaseModel):
    model_config = _CAMEL

    groupnum: str = Field(alias="groupNum")
    startdt: date = Field(alias="startDate")
    enddt: date | None = Field(default=None, alias="endDate")
    covtype: str | None = Field(default=None, alias="coverageType")

    @model_validator(mode="after")
    def enddt_not_before_startdt(self) -> EligibilityCreate:
        if self.enddt is not None and self.enddt < self.startdt:
            raise InvalidEligibilityDataException(
                "End Date must be on or after Start Date."
            )
        return self


class EligibilityUpdate(BaseModel):
    model_config = _CAMEL

    groupnum: str = Field(alias="groupNum")
    startdt: date = Field(alias="startDate")
    enddt: date | None = Field(default=None, alias="endDate")
    covtype: str | None = Field(default=None, alias="coverageType")

    @model_validator(mode="after")
    def enddt_not_before_startdt(self) -> EligibilityUpdate:
        if self.enddt is not None and self.enddt < self.startdt:
            raise InvalidEligibilityDataException(
                "End Date must be on or after Start Date."
            )
        return self
