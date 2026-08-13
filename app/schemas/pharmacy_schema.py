from __future__ import annotations

from pydantic import Field, model_validator

from app.core.base_model import AppBaseModel as BaseModel
from app.schemas.common_schema import SearchRequest

_CAMEL = {"populate_by_name": True, "from_attributes": True}


class PharmacyInfo(BaseModel):
    model_config = _CAMEL

    nabp: str
    npi: str
    pharmacy_name: str = Field(alias="pharmacyName")
    address: str | None = None
    phone: str | None = None
    fax: str | None = None
    is_24_hour: bool = Field(alias="is24Hour")
    in_network: bool = Field(alias="inNetwork")
    longitude: float | None = None
    latitude: float | None = None


class PharmacySearch(BaseModel):
    model_config = _CAMEL

    name: str | None = None
    nabp: str | None = None
    npi: str | None = None
    city: str | None = None
    state: str | None = Field(None, max_length=2)
    zip_code: str | None = Field(None, alias="zipCode")
    is_24_hour: bool | None = Field(None, alias="is24Hour")
    in_network: bool | None = Field(None, alias="inNetwork")

    @model_validator(mode="after")
    def at_least_one_criterion(self) -> PharmacySearch:
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


class PharmacySearchRequest(BaseModel, SearchRequest[PharmacySearch]):
    pass


class PharmacyLookupRequest(BaseModel):
    model_config = _CAMEL

    nabp: str | None = None
    npi: str | None = None

    @model_validator(mode="after")
    def exactly_one_identifier(self) -> PharmacyLookupRequest:
        if not self.nabp and not self.npi:
            from app.core.exceptions import MissingSearchCriteriaException

            raise MissingSearchCriteriaException(
                "Either 'nabp' or 'npi' must be provided."
            )
        if self.nabp and self.npi:
            from app.core.exceptions import InvalidSearchCriteriaException

            raise InvalidSearchCriteriaException(
                "Provide only one of 'nabp' or 'npi', not both."
            )
        return self
