from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.schemas.common_schema import SearchRequest

_CAMEL = {"populate_by_name": True}


class PrescriberInfo(BaseModel):
    model_config = _CAMEL

    npi: str
    dea: str | None = None
    name: str
    specialty: str | None = None
    address: str
    phone: str | None = None
    fax: str | None = None


class PrescriberSearch(BaseModel):
    model_config = _CAMEL

    name: str | None = None
    npi: str | None = None
    dea: str | None = None
    specialty: str | None = None
    city: str | None = None
    state: str | None = Field(None, max_length=2)

    @model_validator(mode="after")
    def at_least_one_criterion(self) -> PrescriberSearch:
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
