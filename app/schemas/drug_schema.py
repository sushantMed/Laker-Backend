from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.schemas.common_schema import SearchRequest
from app.utils.enums import BrandGeneric, Maintenance
from app.utils.pagination import PaginationRequest, SortRequest

_CAMEL = {"populate_by_name": True}


class DrugInfo(BaseModel):
    model_config = _CAMEL

    ndc: str
    gpi: str
    drug_name: str = Field(alias="drugName")
    brand_generic: BrandGeneric = Field(alias="brandGeneric")
    maintenance: Maintenance
    desi: str | None = None
    tier: int | None = None
    formulary_status: str | None = Field(None, alias="formularyStatus")
    repackage_ind: bool = Field(alias="repackageInd")


class DrugSearch(BaseModel):
    model_config = _CAMEL

    name: str | None = None
    ndc: str | None = None
    gpi: str | None = None
    brand_generic: BrandGeneric | None = Field(None, alias="brandGeneric")
    maintenance: Maintenance | None = None
    tier: int | None = Field(None, ge=0, le=5)

    @model_validator(mode="after")
    def at_least_one_criterion(self) -> DrugSearch:
        has_criteria = any(
            [
                self.name,
                self.ndc,
                self.gpi,
                self.brand_generic,
                self.maintenance,
                self.tier,
            ]
        )
        if not has_criteria:
            from app.core.exceptions import MissingSearchCriteriaException

            raise MissingSearchCriteriaException(
                "At least one search criterion (name, ndc, gpi, brandGeneric, "
                "maintenance, or tier) must be provided."
            )
        return self


class DrugSearchRequest(SearchRequest[DrugSearch]):
    pass


class GpiLookupRequest(PaginationRequest, SortRequest):
    pass
