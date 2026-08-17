from __future__ import annotations

from datetime import date, datetime

from pydantic import ConfigDict, Field, field_validator, model_validator  # type: ignore
from pydantic.alias_generators import to_camel  # type: ignore

from app.core.base_model import AppBaseModel as BaseModel
from app.schemas.common_schema import SearchRequest
from app.utils.enums import PAStatus
from app.utils.pagination import PaginationRequest

_CAMEL = {"populate_by_name": True}

# The PA grid lets the user pull the whole result set in one page, so this
# endpoint allows a far larger pageSize than the shared 100-row default.
_PA_PAGE_SIZE_MAX = 10_000

_DRUG_NAME_MAX = 70
_PROVIDER_MAX = 50
_REASON_CODE_MAX = 20
_NOTES_MAX = 2000
_DIAGNOSIS_MAX = 100

_NDC_PATTERN = r"^\d{11}$"
_GPI_PATTERN = r"^[A-Za-z0-9]{14}$"

# NDCs are stored 11 wide. The grid lets the user key a short one, which is
# left-padded with zeros before it hits the query.
_NDC_LENGTH = 11
_NDC_SEARCH_MIN = 9


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


class PASearchResult(BaseModel):
    model_config = _CAMEL

    pa_id: str = Field(alias="paId")
    member_id: str | None = Field(None, alias="memberId")
    first_name: str | None = Field(None, alias="firstName")
    last_name: str | None = Field(None, alias="lastName")
    drug_name: str | None = Field(None, alias="drugName")
    ndc: str | None = None
    provider: str | None = None
    eff_date: date | None = Field(None, alias="effDate")
    term_date: date | None = Field(None, alias="termDate")
    status: PAStatus


class PAMemberSearchResult(BaseModel):
    """
    Row shape for /members/{memberId}/prior-auth/search.

    The member grid wants the PA's own columns, not the resolved member/drug
    details that PASearchResult carries -- the member is already known from the
    path.
    """

    model_config = _CAMEL

    auth_num: str = Field(alias="authNum")
    ndc: str | None = None
    gpi: str | None = None
    drug_name_ndc: str | None = Field(None, alias="drugNameNdc")
    drug_name_gpi: str | None = Field(None, alias="drugNameGpi")
    action: str | None = None
    eff_date: date | None = Field(None, alias="effDate")
    term_date: date | None = Field(None, alias="termDate")
    last_user: str | None = Field(None, alias="lastUser")
    subscriber_num: str | None = Field(None, alias="subscriberNum")
    person_codes: str | None = Field(None, alias="personCodes")


class PADetail(PASearchResult):
    model_config = _CAMEL

    gpi: str | None = None
    group_number: str | None = Field(None, alias="groupNumber")
    person_codes: str | None = Field(None, alias="personCodes")
    prescriber_npi: str | None = Field(None, alias="prescriberNpi")
    pharmacy_nabp: str | None = Field(None, alias="pharmacyNabp")

    brand_generic: str | None = Field(None, alias="brandGeneric")
    diagnosis: str | None = None
    second_diagnosis: str | None = Field(None, alias="secondDiagnosis")
    dea_class: str | None = Field(None, alias="deaClass")
    reason_code: str | None = Field(None, alias="reasonCode")
    notes: str | None = None
    message: str | None = None

    refills: str | None = None
    max_daily_dose: str | None = Field(None, alias="maxDailyDose")
    max_script_qty: str | None = Field(None, alias="maxScriptQty")
    max_script_days: str | None = Field(None, alias="maxScriptDays")
    max_scripts: int | None = Field(None, alias="maxScripts")

    source: str | None = None
    auth_by: str | None = Field(None, alias="authBy")
    called_in_by: str | None = Field(None, alias="calledInBy")
    appeal: str | None = None
    denial: str | None = None
    request_received: date | None = Field(None, alias="requestReceived")
    documentation_received: date | None = Field(None, alias="documentationReceived")
    request_approved: date | None = Field(None, alias="requestApproved")
    member_notified: date | None = Field(None, alias="memberNotified")
    days_old: int | None = Field(None, alias="daysOld")

    created_by: str | None = Field(None, alias="createdBy")
    created_at: datetime | None = Field(None, alias="createdAt")
    changed_by: str | None = Field(None, alias="changedBy")
    changed_at: datetime | None = Field(None, alias="changedAt")


class PASearch(BaseModel):
    model_config = _CAMEL

    pa_id: str | None = Field(None, alias="paId")
    member_id: str | None = Field(None, alias="memberId", max_length=50)
    drug_name: str | None = Field(None, alias="drugName")
    ndc: str | None = None
    status: PAStatus | None = None
    eff_date_from: date | None = Field(None, alias="effDateFrom")
    eff_date_to: date | None = Field(None, alias="effDateTo")

    @field_validator("pa_id", "member_id", "drug_name", "ndc", mode="before")
    @classmethod
    def strip_and_blank_to_none(cls, v: str | None) -> str | None:
        return _blank_to_none(v)

    @model_validator(mode="after")
    def validate_search_criteria(self) -> PASearch:
        has_any_criteria = any(
            [
                self.pa_id,
                self.member_id,
                self.drug_name,
                self.ndc,
                self.status,
                self.eff_date_from,
                self.eff_date_to,
            ]
        )
        if not has_any_criteria:
            from app.core.exceptions import NoSearchCriteriaException

            raise NoSearchCriteriaException(
                "At least one search criterion (paId, memberId, drugName, ndc, "
                "status, effDateFrom, or effDateTo) must be provided."
            )
        return self

    @model_validator(mode="after")
    def validate_eff_date_range(self) -> PASearch:
        _require_ordered_dates(self.eff_date_from, self.eff_date_to)
        return self


class PASearchByMemberPath(BaseModel):
    """
    Criteria for /members/{memberId}/prior-auth/search.

    Only ndc, effDate and termDate are filters; effDate is a lower bound on the
    PA's effdate and termDate an upper bound on its termdate. Every other key in
    the body is ignored, memberId included: the search is already scoped by the
    path.

    ndc must be 9-11 characters and is left-padded with zeros to the stored
    11-character width; blank or absent drops the filter.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "ndc": None,
                "effDate": None,
                "termDate": None,
            }
        },
    )

    ndc: str | None = Field(None, min_length=_NDC_SEARCH_MIN, max_length=_NDC_LENGTH)
    eff_date: date | None = None
    term_date: date | None = None

    @field_validator("ndc", mode="before")
    @classmethod
    def strip_and_blank_to_none(cls, v: str | None) -> str | None:
        return _blank_to_none(v)

    @field_validator("ndc", mode="after")
    @classmethod
    def pad_ndc(cls, v: str | None) -> str | None:
        """A short NDC (e.g. 9 digits) is stored 11 wide -- pad zeros in front."""
        return v.zfill(_NDC_LENGTH) if v else v

    @field_validator("eff_date", "term_date", mode="before")
    @classmethod
    def blank_date_to_none(cls, v):
        """An untouched date box posts "" -- treat it as no filter, not a 422."""
        if isinstance(v, str) and not v.strip():
            return None
        return v


class PAPagination(PaginationRequest):
    """Pagination for the member PA search -- same shape, higher pageSize cap."""

    page_size: int = Field(default=20, ge=1, le=_PA_PAGE_SIZE_MAX, alias="pageSize")


class PASearchRequest(BaseModel, SearchRequest[PASearch]):
    """Envelope for PA1 -- criteria plus sort and pagination."""


class PASearchRequestByMemberPath(BaseModel, SearchRequest[PASearchByMemberPath]):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "searchRequest": {
                    "ndc": None,
                    "effDate": None,
                    "termDate": None,
                },
                "sort": {"sortBy": "effDate", "sortDir": "DESC"},
                "pagination": {"page": 1, "pageSize": 20},
            }
        },
    )

    pagination: PAPagination = Field(default_factory=PAPagination)


class PAByEntityQuery(BaseModel, PaginationRequest):
    model_config = _CAMEL

    status: PAStatus | None = None


class CreatePARequest(BaseModel):
    model_config = _CAMEL

    member_id: str = Field(alias="memberId", max_length=50)
    eff_date: date = Field(alias="effDate")
    term_date: date = Field(alias="termDate")
    drug_name: str = Field(alias="drugName", max_length=_DRUG_NAME_MAX)
    ndc: str = Field(pattern=_NDC_PATTERN)
    gpi: str | None = Field(None, pattern=_GPI_PATTERN)
    provider: str | None = Field(None, max_length=_PROVIDER_MAX)
    status: PAStatus
    reason_code: str | None = Field(
        None, alias="reasonCode", max_length=_REASON_CODE_MAX
    )
    notes: str | None = Field(None, max_length=_NOTES_MAX)
    diagnosis: str | None = Field(None, max_length=_DIAGNOSIS_MAX)

    @model_validator(mode="after")
    def validate_term_after_eff(self) -> CreatePARequest:
        _require_ordered_dates(self.eff_date, self.term_date, "effDate", "termDate")
        return self


class UpdatePARequest(BaseModel):
    model_config = _CAMEL

    eff_date: date = Field(alias="effDate")
    term_date: date = Field(alias="termDate")
    drug_name: str = Field(alias="drugName", max_length=_DRUG_NAME_MAX)
    ndc: str = Field(pattern=_NDC_PATTERN)
    gpi: str | None = Field(None, pattern=_GPI_PATTERN)
    provider: str | None = Field(None, max_length=_PROVIDER_MAX)
    status: PAStatus
    reason_code: str | None = Field(
        None, alias="reasonCode", max_length=_REASON_CODE_MAX
    )
    notes: str | None = Field(None, max_length=_NOTES_MAX)
    diagnosis: str | None = Field(None, max_length=_DIAGNOSIS_MAX)

    @model_validator(mode="after")
    def validate_term_after_eff(self) -> UpdatePARequest:
        _require_ordered_dates(self.eff_date, self.term_date, "effDate", "termDate")
        return self


class PatchPARequest(BaseModel):
    model_config = _CAMEL

    status: PAStatus | None = None
    reason_code: str | None = Field(
        None, alias="reasonCode", max_length=_REASON_CODE_MAX
    )
    notes: str | None = Field(None, max_length=_NOTES_MAX)


def _require_ordered_dates(
    start: date | None,
    end: date | None,
    start_label: str = "effDateFrom",
    end_label: str = "effDateTo",
) -> None:
    if start and end and end < start:
        from app.core.exceptions import InvalidDateRangeException

        raise InvalidDateRangeException(
            f"{end_label} ({end}) must be >= {start_label} ({start})."
        )
