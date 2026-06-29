from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.schemas.common_schema import SearchRequest

_CAMEL = {"populate_by_name": True}


class PrescriberInfo(BaseModel):
    model_config = _CAMEL

    npi: str
    dea: Optional[str] = None
    name: str
    specialty: Optional[str] = None
    address: str
    phone: Optional[str] = None
    fax: Optional[str] = None


class PrescriberSearch(BaseModel):
    model_config = _CAMEL

    name: Optional[str] = None
    npi: Optional[str] = None
    dea: Optional[str] = None
    specialty: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = Field(None, max_length=2)

    @model_validator(mode="after")
    def at_least_one_criterion(self) -> "PrescriberSearch":
        has_criteria = any(
            [
                self.name,
                self.npi,
                self.dea,
                self.specialty,
                self.city,
                self.state,
            ]
        )
        if not has_criteria:
            from app.core.exceptions import MissingSearchCriteriaException

            raise MissingSearchCriteriaException(
                "At least one search criterion (name, npi, dea, specialty, city, "
                "or state) must be provided."
            )
        return self


class PrescriberSearchRequest(SearchRequest[PrescriberSearch]):
    pass
