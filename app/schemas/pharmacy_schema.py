from __future__ import annotations

from pydantic import Field, field_validator, model_validator

from app.core.base_model import AppBaseModel as BaseModel
from app.core.exceptions import InvalidSearchCriteriaException
from app.schemas.common_schema import SearchRequest
from app.utils.pagination import PaginationRequest

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
    longitude: float | None = None
    latitude: float | None = None
    zip: str | None = Field(alias="zipCode")


class PharmacySearch(BaseModel):
    model_config = _CAMEL

    name: str | None = None
    nabp: str | None = None
    npi: str | None = None
    city: str | None = None
    state: str | None = Field(None, max_length=2)
    zip_code: str | None = Field(None, alias="zipCode")
    is_24_hour: bool | None = Field(None, alias="is24Hour")
    longitude: float | None = None
    latitude: float | None = None

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


class PharmacyLookupRequest(PaginationRequest):
    model_config = _CAMEL

    nabp: str | None = None
    npi: str | None = None
    zip_code: str | None = Field(
        None,
        alias="zipCode",
        description="A five-digit U.S. ZIP code, optionally followed by ZIP+4.",
    )
    radius: int | None = Field(10, ge=0)  # in miles
    is_24_hour: bool | None = Field(False, alias="is24Hour")

    @field_validator("zip_code")
    @classmethod
    def validate_us_zip_code(cls, zip_code: str | None) -> str | None:
        if zip_code is None:
            return None

        is_five_digit_zip = len(zip_code) == 5 and zip_code.isdigit()
        is_zip_plus_four = (
            len(zip_code) == 10
            and zip_code[5] == "-"
            and zip_code[:5].isdigit()
            and zip_code[6:].isdigit()
        )
        if not (is_five_digit_zip or is_zip_plus_four):
            raise InvalidSearchCriteriaException(
                "zipCode must be a valid U.S. ZIP code (for example, 62704 or 62704-1234)."
            )
        return zip_code

    @model_validator(mode="after")
    def exactly_one_identifier(self) -> PharmacyLookupRequest:
        if not self.nabp and not self.npi and not self.zip_code:
            from app.core.exceptions import MissingSearchCriteriaException

            raise MissingSearchCriteriaException(
                "Either 'nabp', 'npi', or 'zipCode' must be provided."
            )
        if sum(bool(value) for value in (self.nabp, self.npi, self.zip_code)) > 1:
            raise InvalidSearchCriteriaException(
                "Provide only one of 'nabp', 'npi', or 'zipCode', not all three."
            )
        return self
