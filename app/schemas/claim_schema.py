"""
Claim module schemas (Pydantic v2).

Naming convention: camelCase aliases for API surface, snake_case internally.
All validation uses @model_validator(mode="after").
"""

from __future__ import annotations

import calendar
from datetime import date

from pydantic import Field, field_validator, model_validator  # type:ignore

from app.core.base_model import AppBaseModel as BaseModel
from app.schemas.common_schema import SearchRequest
from app.utils.pagination import PaginationRequest

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
    date_filled: date = Field(alias="filledDate")
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

    date_filled: date = Field(None, alias="filledDate")
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


_MAX_DATE_RANGE_MONTHS = 12


def _add_months(d: date, months: int) -> date:
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


class ClaimSearch(BaseModel):
    """
    Search criteria for POST /claims/search (and the member-scoped variant).

    Business rules (per the C1 spec):
    - memberId, authNum, and/or a startDate/endDate dateFilled range may be
      supplied.
    - startDate and endDate must be supplied together (both or neither), and
      when both are given, endDate must be on/after startDate and the span
      between them may not exceed 12 months.
    - If memberId is NOT provided, startDate/endDate are required — an
      auth-num-only search without a member is too expensive to run
      unbounded.
    - If memberId IS provided, the date range is optional.
    """

    model_config = _CAMEL

    member_id: str | None = Field(None, alias="memberId")
    auth_num: str | None = Field(None, alias="authNum")
    start_date: date | None = Field(None, alias="startDate")
    end_date: date | None = Field(None, alias="endDate")

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
        from app.core.exceptions import (
            InvalidDateRangeException,
            NoSearchCriteriaException,
        )

        has_any_criteria = any(
            [self.member_id, self.auth_num, self.start_date, self.end_date]
        )
        if not has_any_criteria:
            raise NoSearchCriteriaException(
                "At least one search criterion (memberId, authNum, "
                "or startDate/endDate) must be provided."
            )

        if bool(self.start_date) != bool(self.end_date):
            raise InvalidDateRangeException(
                "startDate and endDate must be provided together."
            )

        if not self.member_id and not self.start_date:
            raise NoSearchCriteriaException(
                "startDate and endDate are required when memberId is not provided."
            )

        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise InvalidDateRangeException(
                    "endDate must be on or after startDate."
                )
            if self.end_date > _add_months(self.start_date, _MAX_DATE_RANGE_MONTHS):
                raise InvalidDateRangeException(
                    "The span between start-date and end-date must not "
                    f"exceed {_MAX_DATE_RANGE_MONTHS} months."
                )

        return self


class ClaimSearchRequest(BaseModel, SearchRequest[ClaimSearch]):
    pass


class ClaimsByEntityQuery(BaseModel, PaginationRequest):
    """
    Shared query-param — claim history scoped to a
    pharmacy (NABP), prescriber (NPI), or drug (NDC), with an optional
    Date Filled upper bound. No sort fields exposed in the spec for these.
    """

    model_config = _CAMEL

    end_date: date | None = Field(None, alias="filledDate")


class ClaimSearchByMemberRequest(BaseModel):
    """
    Request body schema for POST /members/{memberId}/claims/search.

    memberId comes from the path, not from here. All fields are optional
    and sent as a JSON request body; page/pageSize remain query params.

    Business rules:
    - If `recent` is True, none of authNum/filledDate may be supplied.
      Providing both is treated as conflicting intent and rejected with a 422
      rather than silently ignoring the extra filters. The actual trailing
      recent-claims window is computed by ClaimService, not here.
    - filledDate accepts values in a few known formats (not just ISO)
      because the current frontend sends US-style MM/DD/YYYY and sometimes
      leaks its own placeholder text (e.g. "mm/dd/yyyy") as the literal
      value when the field is left unset — see OptionalDateQuery in
      app/schemas/common_types.py for the normalization/parsing logic.
    """

    model_config = _CAMEL

    auth_num: str | None = Field(None, alias="authNum")
    date_filled: date | None = Field(None, alias="filledDate")
    recent: bool = False
    exclude_test_claims: bool = Field(True, alias="excludeTestClaims")

    @field_validator("date_filled", "auth_num", mode="before")
    @classmethod
    def blank_to_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @model_validator(mode="after")
    def validate_recent_is_exclusive(self) -> ClaimSearchByMemberRequest:
        """Reject requests that combine `recent=true` with any explicit filter."""
        if self.recent and (self.auth_num or self.date_filled):
            from app.core.exceptions import (
                InvalidSearchCriteriaException,
            )

            raise InvalidSearchCriteriaException(
                "When recent=true, authNum and filledDate must not be provided."
            )
        return self
