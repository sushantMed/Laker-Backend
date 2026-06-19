"""
Claim module schemas (Pydantic v2).

Naming convention: camelCase aliases for API surface, snake_case internally.
All validation uses @model_validator(mode="after") — never __init__.
"""

from __future__ import annotations

from datetime import date
from typing import Optional
from app.utils.pagination import SortRequest, PaginationRequest

from pydantic import BaseModel, Field, model_validator

from app.schemas.common_schema import SearchRequest


# ── Shared config ────────────────────────────────────────────────────────────

_CAMEL = {"populate_by_name": True}


# ── Pharmacy / Prescriber summaries (embedded in claim detail) ───────────────


class PharmacySummary(BaseModel):
    model_config = _CAMEL

    pharmacy_npi: Optional[str] = Field(None, alias="pharmacyNpi")
    pharmacy_name: Optional[str] = Field(None, alias="pharmacyName")


class PrescriberSummary(BaseModel):
    model_config = _CAMEL

    prescriber_npi: Optional[str] = Field(None, alias="prescriberNpi")
    prescriber_name: Optional[str] = Field(None, alias="prescriberName")


# ── Claim summary (search results list row) ──────────────────────────────────


class ClaimSummary(BaseModel):
    """Lightweight DTO for search result rows — matches the Claims Search grid."""

    model_config = _CAMEL

    auth_num: str = Field(alias="authNum")
    date_filled: date = Field(alias="dateFilled")
    member_id: str = Field(alias="memberId")
    first_name: Optional[str] = Field(None, alias="firstName")
    last_name: Optional[str] = Field(None, alias="lastName")
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
    first_name: Optional[str] = Field(None, alias="firstName")
    last_name: Optional[str] = Field(None, alias="lastName")

    rx_number: str = Field(alias="rxNumber")
    drug: str
    ndc: str

    date_filled: date = Field(alias="dateFilled")
    date_written: Optional[date] = Field(None, alias="dateWritten")
    quantity: Optional[float] = None
    days_supply: Optional[int] = Field(None, alias="daysSupply")
    refills_remaining: Optional[int] = Field(None, alias="refillsRemaining")

    pharmacy: Optional[PharmacySummary] = None
    prescriber: Optional[PrescriberSummary] = None

    ingredient_cost: Optional[float] = Field(None, alias="ingredientCost")
    dispensing_fee: Optional[float] = Field(None, alias="dispensingFee")
    copay: Optional[float] = None
    total_paid: Optional[float] = Field(None, alias="totalPaid")

    is_test_claim: bool = Field(False, alias="isTestClaim")
    plan_id: Optional[str] = Field(None, alias="planId")


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

    member_id: Optional[str] = Field(None, alias="memberId")
    auth_num: Optional[str] = Field(None, alias="authNum")
    date_filled_start: Optional[date] = Field(None, alias="dateFilledStart")
    date_filled_end: Optional[date] = Field(None, alias="dateFilledEnd")

    # Checked by default in the UI ("Exclude Test Claims")
    exclude_test_claims: bool = Field(True, alias="excludeTestClaims")

    @model_validator(mode="after")
    def validate_search_criteria(self) -> "ClaimSearch":
        has_any_criteria = any(
            [
                self.member_id,
                self.auth_num,
                self.date_filled_start,
                self.date_filled_end,
            ]
        )
        if not has_any_criteria:
            from core.exceptions import NoSearchCriteriaException

            raise NoSearchCriteriaException(
                "At least one search criterion (memberId, authNum, "
                "dateFilledStart, or dateFilledEnd) must be provided."
            )

        if not self.member_id and not (
            self.date_filled_start and self.date_filled_end
        ):
            from core.exceptions import NoSearchCriteriaException

            raise NoSearchCriteriaException(
                "A full dateFilled range (dateFilledStart and dateFilledEnd) "
                "is required when memberId is not provided."
            )
        return self

    @model_validator(mode="after")
    def validate_date_filled_range(self) -> "ClaimSearch":
        if self.date_filled_start and self.date_filled_end:
            if self.date_filled_end < self.date_filled_start:
                from core.exceptions import InvalidDateRangeException

                raise InvalidDateRangeException(
                    f"dateFilledEnd ({self.date_filled_end}) must be >= "
                    f"dateFilledStart ({self.date_filled_start})."
                )

            span_days = (self.date_filled_end - self.date_filled_start).days
            if span_days > _MAX_DATE_RANGE_DAYS:
                from core.exceptions import InvalidDateRangeException

                raise InvalidDateRangeException(
                    "Date Filled range cannot exceed 12 months "
                    f"(dateFilledStart={self.date_filled_start}, "
                    f"dateFilledEnd={self.date_filled_end})."
                )
        return self


class ClaimSearchRequest(SearchRequest[ClaimSearch]):
    pass




class ClaimsByMemberRequest(PaginationRequest, SortRequest):
    pass




class ClaimsByEntityQuery(PaginationRequest):
    """
    Shared query-param shape for C5/C6/C7 — claim history scoped to a
    pharmacy (NABP), prescriber (NPI), or drug (NDC), with an optional
    Date Filled range. No sort fields exposed in the spec for these.
    """

    model_config = _CAMEL

    start_date: Optional[date] = Field(None, alias="startDate")
    end_date: Optional[date] = Field(None, alias="endDate")

    @model_validator(mode="after")
    def validate_date_range(self) -> "ClaimsByEntityQuery":
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                from core.exceptions import InvalidDateRangeException

                raise InvalidDateRangeException(
                    f"endDate ({self.end_date}) must be >= "
                    f"startDate ({self.start_date})."
                )
            span_days = (self.end_date - self.start_date).days
            if span_days > _MAX_DATE_RANGE_DAYS:
                from core.exceptions import InvalidDateRangeException

                raise InvalidDateRangeException(
                    "Date range cannot exceed 12 months "
                    f"(startDate={self.start_date}, endDate={self.end_date})."
                )
        return self