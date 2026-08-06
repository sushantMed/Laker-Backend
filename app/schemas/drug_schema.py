from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.common_schema import SearchRequest
from app.utils.enums import BrandGeneric, Maintenance
from app.utils.pagination import PaginationRequest, SortRequest

_CAMEL = {"populate_by_name": True}

# NDCs are searched as an exact match. Callers may supply a 9-digit NDC, which
# is left-padded with "00" to reach the 11-digit form stored in `drugs.ndc`.
_NDC_MIN_LENGTH = 9
_NDC_MAX_LENGTH = 11
_NDC_PAD = "00"


class DrugInfo(BaseModel):
    model_config = _CAMEL

    ndc: str
    gpi: str
    drug_name: str = Field(alias="drugName")
    brand_generic: BrandGeneric = Field(alias="brandGeneric")
    maintenance: Maintenance
    desi: str | None = None
    formulary_status: str | None = Field(None, alias="formularyStatus")
    repackage_ind: bool = Field(alias="repackageInd")


class DrugSearch(BaseModel):
    model_config = _CAMEL

    name: str | None = None
    ndc: str | None = None
    gpi: str | None = None
    brand_generic: BrandGeneric | None = Field(None, alias="brandGeneric")
    maintenance: Maintenance | None = None

    @field_validator("name", "ndc", "gpi", mode="before")
    @classmethod
    def strip_and_blank_to_none(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        return v or None

    @model_validator(mode="after")
    def normalize_ndc(self) -> DrugSearch:
        """Validate NDC length and left-pad a 9-digit NDC to its 11-digit form."""
        if not self.ndc:
            return self

        if not _NDC_MIN_LENGTH <= len(self.ndc) <= _NDC_MAX_LENGTH:
            from app.core.exceptions import InvalidSearchCriteriaException

            raise InvalidSearchCriteriaException(
                f"ndc must be between {_NDC_MIN_LENGTH} and {_NDC_MAX_LENGTH} "
                "characters."
            )

        if len(self.ndc) == _NDC_MIN_LENGTH:
            self.ndc = f"{_NDC_PAD}{self.ndc}"
        return self

    @model_validator(mode="after")
    def at_least_one_criterion(self) -> DrugSearch:
        has_criteria = any(
            [
                self.name,
                self.ndc,
                self.gpi,
                self.brand_generic,
                self.maintenance,
            ]
        )
        if not has_criteria:
            from app.core.exceptions import MissingSearchCriteriaException

            raise MissingSearchCriteriaException(
                "At least one search criterion (name, ndc, gpi, brandGeneric, "
                "or maintenance) must be provided."
            )
        return self


class DrugSearchRequest(SearchRequest[DrugSearch]):
    pass


class GpiLookupRequest(PaginationRequest, SortRequest):
    pass
