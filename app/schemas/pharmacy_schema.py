from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.schemas.common_schema import SearchRequest

_CAMEL = {"populate_by_name": True}


class PharmacyInfo(BaseModel):
    model_config = _CAMEL

    nabp: str
    npi: str
    pharmacy_name: str = Field(alias="pharmacyName")
    address: str
    phone: str
    fax: Optional[str] = None
    is_24_hour: bool = Field(alias="is24Hour")
    in_network: bool = Field(alias="inNetwork")


class PharmacySearch(BaseModel):
    model_config = _CAMEL

    name: Optional[str] = None
    nabp: Optional[str] = None
    npi: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = Field(None, max_length=2)
    zip_code: Optional[str] = Field(None, alias="zipCode")
    is_24_hour: Optional[bool] = Field(None, alias="is24Hour")
    in_network: Optional[bool] = Field(None, alias="inNetwork")

    @model_validator(mode="after")
    def at_least_one_criterion(self) -> "PharmacySearch":
        has_criteria = any(
            [
                self.name,
                self.nabp,
                self.npi,
                self.city,
                self.state,
                self.zip_code,
            ]
        )
        if not has_criteria:
            from app.core.exceptions import MissingSearchCriteriaException

            raise MissingSearchCriteriaException(
                "At least one search criterion (name, nabp, npi, city, state, "
                "or zipCode) must be provided."
            )
        return self


class PharmacySearchRequest(SearchRequest[PharmacySearch]):
    pass
