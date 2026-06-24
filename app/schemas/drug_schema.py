from __future__ import annotations

from typing import Optional

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
    desi: Optional[str] = None
    tier: Optional[int] = None
    formulary_status: Optional[str] = Field(None, alias="formularyStatus")
    repackage_ind: bool = Field(alias="repackageInd")


class DrugSearch(BaseModel):
    model_config = _CAMEL

    name: Optional[str] = None
    ndc: Optional[str] = None
    gpi: Optional[str] = None
    brand_generic: Optional[BrandGeneric] = Field(None, alias="brandGeneric")
    maintenance: Optional[Maintenance] = None
    tier: Optional[int] = Field(None, ge=1, le=5)

    @model_validator(mode="after")
    def at_least_one_criterion(self) -> "DrugSearch":
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
