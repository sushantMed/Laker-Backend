"""
Member module schemas (Pydantic v2).

Naming convention: camelCase aliases for API surface, snake_case internally.
All validation uses @model_validator(mode="after") — never __init__.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.schemas.common_schema import SearchRequest
from app.utils.enums import CoverageType, FamilyRole, Gender, MemberStatus, RelCode
from app.utils.pagination import PaginationRequest, SortRequest

# ── Shared config ────────────────────────────────────────────────────────────

_CAMEL = {"populate_by_name": True}


def _calculate_age(date_of_birth: date) -> str:
    today = date.today()
    age = today.year - date_of_birth.year
    if today < date_of_birth.replace(year=today.year):
        age -= 1
    return str(age)


# ── Address ──────────────────────────────────────────────────────────────────


class MemberAddressSchema(BaseModel):
    model_config = _CAMEL

    address1: str | None = None
    address2: str | None = None
    city: str | None = None
    state: str | None = Field(None, max_length=2)
    zip: str | None = Field(None, max_length=10)


# ── Plan summary (embedded in member responses) ──────────────────────────────


class PlanSummary(BaseModel):
    model_config = _CAMEL

    plan_id: str = Field(alias="planId")
    carrier: str
    group_name: str | None = Field(None, alias="groupName")
    group_number: str | None = Field(None, alias="groupNumber")
    rx_bin: str | None = Field(None, alias="rxBin")
    rx_pcn: str | None = Field(None, alias="rxPcn")


# ── Member summary (search results list row) ─────────────────────────────────


class MemberSummary(BaseModel):
    """Lightweight DTO for search result rows."""

    model_config = _CAMEL

    member_id: str = Field(alias="memberId")
    subscriber_member_id: str | None = Field(None, alias="subscriberMemberId")
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    mi: str | None = None
    date_of_birth: date = Field(alias="dateOfBirth")
    age: str = ""
    gender: Gender | None = None
    status: MemberStatus
    person_code: str = Field(alias="personCode")
    family_position: str | None = Field(None, alias="familyPosition")
    rel_code: str = Field(alias="relCode")
    role: FamilyRole = Field(alias="role")
    cov_type: CoverageType | None = Field(None, alias="covType")
    insured_id: str | None = Field(None, alias="insuredId")
    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")
    plan_id: str | None = Field(None, alias="planId")
    # Carrier pulled from joined Plan — useful for list display
    carrier: str | None = None


# ── Member detail (single member GET) ────────────────────────────────────────


class MemberDetail(BaseModel):
    """Full member record including address and plan."""

    model_config = _CAMEL

    member_id: str = Field(alias="memberId")
    subscriber_member_id: str | None = Field(None, alias="subscriberMemberId")

    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    mi: str | None = None

    date_of_birth: date = Field(alias="dateOfBirth")
    age: str = ""
    gender: Gender | None = None
    ssn: str | None = None
    family_position: str | None = Field(None, alias="familyPosition")
    cov_type: CoverageType | None = Field(None, alias="covType")
    phone: str | None = None
    email: str | None = None
    language_preference: str | None = Field(None, alias="languagePreference")

    insured_id: str | None = Field(None, alias="insuredId")
    person_code: str = Field(alias="personCode")
    rel_code: str = Field(alias="relCode")
    role: FamilyRole = Field(alias="role")
    laker_pc: str | None = Field(None, alias="lakerPc")
    prev_card_id: str | None = Field(None, alias="prevCardId")

    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")
    status: MemberStatus

    plan: PlanSummary | None = None
    address: MemberAddressSchema | None = None


# ── Eligibility response ──────────────────────────────────────────────────────


class EligibilityResponse(BaseModel):
    model_config = _CAMEL

    member_id: str = Field(alias="memberId")
    status: MemberStatus
    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")


# ── Search ────────────────────────────────────────────────────────────────────


class MemberSearch(BaseModel):
    """
    Search criteria.  At least one field must be non-null.
    Validation is done via model_validator (Pydantic v2 idiomatic).
    """

    model_config = _CAMEL

    carrier: str | None = None
    member_id: str | None = Field(None, alias="memberId")
    first_name: str | None = Field(None, alias="firstName")
    last_name: str | None = Field(None, alias="lastName")
    mi: str | None = None
    date_of_birth: date | None = Field(None, alias="dateOfBirth")

    search_by_prev_card_id: bool = Field(False, alias="searchByPrevCardId")
    include_termed_members: bool = Field(False, alias="includeTermedMembers")

    @model_validator(mode="after")
    def at_least_one_criterion(self) -> MemberSearch:
        has_criteria = any(
            [
                self.carrier,
                self.member_id,
                self.first_name,
                self.last_name,
                self.mi,
                self.date_of_birth,
            ]
        )
        if not has_criteria:
            from app.core.exceptions import MissingSearchCriteriaException

            raise MissingSearchCriteriaException(
                "At least one search criterion (carrier, memberId, firstName, "
                "lastName, mi, or dateOfBirth) must be provided."
            )
        return self


class MemberSearchRequest(SearchRequest[MemberSearch]):
    pass


# ── Add family member request ──────────────────────────────────────────────────


class AddFamilyMemberRequest(BaseModel):
    """
    Request body for POST /members/{memberId}/family.
    Adds a dependent or spouse under the subscriber identified by memberId.
    """

    model_config = _CAMEL

    first_name: str = Field(alias="firstName", min_length=1, max_length=100)
    last_name: str = Field(alias="lastName", min_length=1, max_length=100)
    mi: str | None = Field(None, max_length=1)

    date_of_birth: date = Field(alias="dateOfBirth")
    gender: Gender | None = None
    ssn: str | None = None

    phone: str | None = None
    email: EmailStr | None = None
    language_preference: str | None = Field(
        None, alias="languagePreference", max_length=10
    )

    insured_id: str | None = Field(None, alias="insuredId", max_length=50)
    rel_code: str = Field(alias="relCode")
    cov_type: CoverageType | None = Field(None, alias="covType")
    laker_pc: str | None = Field(None, alias="lakerPc", max_length=20)
    prev_card_id: str | None = Field(None, alias="prevCardId", max_length=50)

    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")

    plan_id: str | None = Field(None, alias="planId")

    address: MemberAddressSchema | None = None

    @model_validator(mode="after")
    def validate_eligibility_dates(self) -> AddFamilyMemberRequest:
        if self.end_date < self.start_date:
            from app.core.exceptions import InvalidEligibilityException

            raise InvalidEligibilityException(
                f"endDate ({self.end_date}) must be >= startDate ({self.start_date})."
            )
        return self

    @model_validator(mode="after")
    def validate_rel_code_not_cardholder(self) -> AddFamilyMemberRequest:
        if self.rel_code == RelCode.CARDHOLDER.value:
            from app.core.exceptions import InvalidFamilyRelationshipException

            raise InvalidFamilyRelationshipException(
                "Cannot add a Cardholder (relCode=01) as a family member. "
                "Use relCode=02 (Spouse) or 03+ (Dependent Child)."
            )
        return self


class FamilyMembersRequest(PaginationRequest, SortRequest):
    pass
