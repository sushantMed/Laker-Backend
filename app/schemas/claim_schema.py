"""
Claim module schemas (Pydantic v2).

Naming convention: camelCase aliases for API surface, snake_case internally.
All validation uses @model_validator(mode="after").
"""

from __future__ import annotations

from datetime import date, timedelta

from pydantic import (  # type:ignore
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from pydantic.alias_generators import to_camel  # type:ignore

from app.core.base_model import AppBaseModel as BaseModel
from app.core.config import settings
from app.schemas.common_schema import SearchRequest
from app.utils.pagination import PaginationRequest, SortRequest

# ── Shared config ────────────────────────────────────────────────────────────

_CAMEL = {"populate_by_name": True}


# ── Pharmacy / Prescriber summaries (embedded in claim detail) ───────────────


class PharmacySummary(BaseModel):
    model_config = _CAMEL

    pharmacy_npi: str | None = Field(None, alias="pharmacyNpi")
    pharmacy_name: str | None = Field(None, alias="pharmacyName")


class PrescriberSummary(BaseModel):
    model_config = _CAMEL

    prescriber_npi: str | None = Field(None, alias="prescriberNpi")
    prescriber_name: str | None = Field(None, alias="prescriberName")


# ── Claim summary (search results list row) ──────────────────────────────────


class ClaimSummary(BaseModel):
    """Lightweight DTO for search result rows — matches the Claims Search grid."""

    model_config = _CAMEL

    auth_num: str = Field(alias="authNum")
    date_filled: date = Field(alias="endDate")
    date_written: date | None = Field(None, alias="startDate")
    member_id: str = Field(alias="memberId")
    first_name: str | None = Field(None, alias="firstName")
    last_name: str | None = Field(None, alias="lastName")
    rx_number: str = Field(alias="rxNumber")
    drug: str
    ndc: str
    is_test_claim: bool = Field(False, alias="isTestClaim")


# ── Claim detail (single claim GET) ───────────────────────────────────────────


class ClaimDetail(BaseModel):
    """Full claim record including pharmacy, prescriber, and cost breakdown."""

    model_config = _CAMEL

    claim_id: str = Field(alias="claimId")
    auth_num: str = Field(alias="authNum")
    member_id: str = Field(alias="memberId")
    first_name: str | None = Field(None, alias="firstName")
    last_name: str | None = Field(None, alias="lastName")

    rx_number: str = Field(alias="rxNumber")
    drug: str
    ndc: str

    date_filled: date = Field(None, alias="endDate")
    date_written: date | None = Field(None, alias="startDate")
    quantity: float | None = None
    days_supply: int | None = Field(None, alias="daysSupply")
    refills_remaining: int | None = Field(None, alias="refillsRemaining")

    pharmacy: PharmacySummary | None = None
    prescriber: PrescriberSummary | None = None

    ingredient_cost: float | None = Field(None, alias="ingredientCost")
    dispensing_fee: float | None = Field(None, alias="dispensingFee")
    copay: float | None = None
    total_paid: float | None = Field(None, alias="totalPaid")

    is_test_claim: bool = Field(False, alias="isTestClaim")
    plan_id: str | None = Field(None, alias="planId")


# ── Search ────────────────────────────────────────────────────────────────────


_MAX_DATE_RANGE_DAYS = 366  # ~12 months


class ClaimSearch(BaseModel):
    """
    Search criteria for POST /claims/search (and the member-scoped variant).

    Business rules (per the C1 spec):
    - memberId, authNum, and/or a dateFilled range may be supplied.
    - If memberId is NOT provided, a full dateFilled range (start AND end)
      is required — open-ended or auth-num-only searches without a member
      are too expensive to run unbounded.
    - The dateFilled range, when supplied, cannot exceed 12 months.
    """

    model_config = _CAMEL

    member_id: str | None = Field(None, alias="memberId")
    auth_num: str | None = Field(None, alias="authNum")
    date_filled: date | None = Field(None, alias="endDate")
    date_written: date | None = Field(None, alias="startDate")

    # Checked by default in the UI ("Exclude Test Claims")
    exclude_test_claims: bool = Field(True, alias="excludeTestClaims")

    @field_validator("auth_num", "member_id", mode="before")
    @classmethod
    def strip_and_blank_to_none(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        return v or None

    @model_validator(mode="after")
    def validate_search_criteria(self) -> ClaimSearch:
        has_any_criteria = any(
            [
                self.member_id,
                self.auth_num,
                self.date_filled,
                self.date_written,
            ]
        )
        if not has_any_criteria:
            from app.core.exceptions import NoSearchCriteriaException

            raise NoSearchCriteriaException(
                "At least one search criterion (memberId, authNum, "
                "startDate, or endDate) must be provided."
            )

        if not self.member_id and not (self.date_filled and self.date_written):
            from app.core.exceptions import NoSearchCriteriaException

            raise NoSearchCriteriaException(
                "A full dateFilled range (startDate and endDate) "
                "is required when memberId is not provided."
            )
        return self

    @model_validator(mode="after")
    def validate_date_filled_range(self) -> ClaimSearch:
        if self.date_filled and self.date_written:
            if self.date_filled < self.date_written:
                from app.core.exceptions import InvalidDateRangeException

                raise InvalidDateRangeException(
                    f"endDate ({self.date_filled}) must be >= "
                    f"startDate ({self.date_written})."
                )

            span_days = (self.date_filled - self.date_written).days
            if span_days > _MAX_DATE_RANGE_DAYS:
                from app.core.exceptions import InvalidDateRangeException

                raise InvalidDateRangeException(
                    "Date Filled range cannot exceed 12 months "
                    f"(endDate={self.date_filled}, "
                    f"startDate={self.date_written})."
                )
        return self


class ClaimSearchByMemberPath(BaseModel):
    """
    Search criteria for /members/{memberId}/claims/search.
    memberId comes from path — no validation needed in body.
    Date range and other filters are all optional.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "authNum": None,
                "startDate": None,
                "endDate": None,
                "excludeTestClaims": True,
            }
        },
    )

    # memberId intentionally excluded — comes from path param
    auth_num: str | None = None
    date_filled: date | None = None
    date_written: date | None = None
    exclude_test_claims: bool = True

    @model_validator(mode="after")
    def validate_date_filled_range(self) -> ClaimSearchByMemberPath:
        if self.date_filled and self.date_written:
            if self.date_written > self.date_filled:
                from app.core.exceptions import InvalidDateRangeException

                raise InvalidDateRangeException(
                    f"endDate ({self.date_written}) must be >= "
                    f"startDate ({self.date_filled})."
                )
            span_days = (self.date_written - self.date_filled).days
            if span_days > _MAX_DATE_RANGE_DAYS:
                from app.core.exceptions import InvalidDateRangeException

                raise InvalidDateRangeException(
                    "Date Filled range cannot exceed 12 months."
                )
        return self


class ClaimSearchRequestByMemberPath(BaseModel, SearchRequest[ClaimSearchByMemberPath]):
    """
    Full request envelope — /members/{memberId}/claims/search.
    memberId is taken from path param, not from body.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "searchRequest": {
                    "authNum": None,
                    "startDate": None,
                    "endDate": None,
                    "excludeTestClaims": True,
                },
                "sort": {"sortBy": "id", "sortDir": "ASC"},
                "pagination": {"page": 1, "pageSize": 20},
            }
        },
    )


class ClaimSearchRequest(BaseModel, SearchRequest[ClaimSearch]):
    pass


class ClaimsByMemberRequest(BaseModel, PaginationRequest, SortRequest):
    pass


class ClaimsByEntityQuery(BaseModel, PaginationRequest):
    """
    Shared query-param — claim history scoped to a
    pharmacy (NABP), prescriber (NPI), or drug (NDC), with an optional
    Date Filled range. No sort fields exposed in the spec for these.
    """

    model_config = _CAMEL

    start_date: date | None = Field(None, alias="startDate")
    end_date: date | None = Field(None, alias="endDate")

    @model_validator(mode="after")
    def validate_date_range(self) -> ClaimsByEntityQuery:
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                from app.core.exceptions import InvalidDateRangeException

                raise InvalidDateRangeException(
                    f"endDate ({self.end_date}) must be >= "
                    f"startDate ({self.start_date})."
                )
            span_days = (self.end_date - self.start_date).days
            if span_days > _MAX_DATE_RANGE_DAYS:
                from app.core.exceptions import InvalidDateRangeException

                raise InvalidDateRangeException(
                    "Date range cannot exceed 12 months "
                    f"(startDate={self.start_date}, endDate={self.end_date})."
                )
        return self


# schema
class ClaimSearchQueryParams(BaseModel):
    """
    Query-parameter schema for GET/POST /members/{memberId}/claims/search.

    memberId comes from the path, not from here. All fields are optional
    and bound individually from the query string via `get_claim_search_params`
    (see app/api/v1/dependencies/claim_deps.py), then assembled into this
    model so validation lives in one place regardless of the route.

    Business rules:
    - If `recent` is True, none of authNum/startDate/endDate may be supplied.
      Providing both is treated as conflicting intent and rejected with a 422
      rather than silently ignoring the extra filters.
    - When `recent` is True, startDate/endDate are auto-populated to a
      trailing `CLAIM_RETRIEVAL_DAYS`-day window ending today, after the
      exclusivity check has run.
    - startDate/endDate accept values in a few known formats (not just ISO)
      because the current frontend sends US-style MM/DD/YYYY and sometimes
      leaks its own placeholder text (e.g. "mm/dd/yyyy") as the literal
      value when a date field is left unset — see OptionalDateQuery in
      app/schemas/common_types.py for the normalization/parsing logic.
    """

    model_config = _CAMEL

    auth_num: str | None = Field(None, alias="authNum")
    date_filled: date | None = Field(None, alias="endDate")
    date_written: date | None = Field(None, alias="startDate")
    recent: bool = False
    exclude_test_claims: bool = Field(True, alias="excludeTestClaims")

    @field_validator("date_filled", "date_written", "auth_num", mode="before")
    @classmethod
    def blank_to_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @model_validator(mode="after")
    def validate_recent_is_exclusive(self) -> ClaimSearchQueryParams:
        """
        Reject requests that combine `recent=true` with any explicit filter.

        Runs before `apply_recent_window` (Pydantic v2 runs `mode="after"`
        validators in declaration order) so the check sees the caller's
        original input, not the auto-filled recent-window dates.
        """
        if self.recent and (self.auth_num or self.date_filled or self.date_written):
            from app.core.exceptions import (
                InvalidSearchCriteriaException,
            )

            raise InvalidSearchCriteriaException(
                "When recent=true, authNum, startDate, and endDate must not be provided."
            )
        return self

    @model_validator(mode="after")
    def apply_recent_window(self) -> ClaimSearchQueryParams:
        """
        Populate startDate/endDate with the trailing recent-claims window
        when `recent` is true. Only reached once exclusivity has already
        been confirmed, so this never overwrites a caller-supplied date.
        """
        if self.recent:
            today = date.today()
            self.date_written = today - timedelta(
                days=settings.recent_claims_window_days
            )
            self.date_filled = today
        return self
