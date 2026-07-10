"""
Member service.

Business logic layer.  Only raises LakerBaseException subclasses —
never ValueError or bare Exception.
HTTP status mapping is the controller's responsibility.
"""

from __future__ import annotations

import hashlib
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.cache_service import CacheService
from app.core.exceptions import (
    DuplicateSpouseException,
    InvalidFamilyRelationshipException,
    MemberNotFoundException,
    PlanNotFoundException,
)
from app.models.member_address_model import MemberAddressModel
from app.models.member_model import MemberModel
from app.repositories.member_repository import MemberRepository
from app.repositories.plan_repository import PlanRepository
from app.schemas.member_schema import (
    AddFamilyMemberRequest,
    EligibilityResponse,
    MemberAddressSchema,
    MemberDetail,
    MemberSearchRequest,
    MemberSummary,
    PlanSummary,
)
from app.utils.enums import FamilyRole, RelCode, derive_status
from app.utils.pagination import PagedResponse, PaginationRequest


def _calculate_age(date_of_birth: date) -> str:
    today = date.today()
    age = today.year - date_of_birth.year
    if today < date_of_birth.replace(year=today.year):
        age -= 1
    return str(age)


def _plan_summary(plan) -> PlanSummary | None:
    if plan is None:
        return None
    return PlanSummary(
        planId=plan.plan_id,
        carrier=plan.carrier,
        groupName=plan.group_name,
        groupNumber=plan.group_number,
        rxBin=plan.rx_bin,
        rxPcn=plan.rx_pcn,
    )


def _address_schema(addr) -> MemberAddressSchema | None:
    if addr is None:
        return None
    return MemberAddressSchema(
        address1=addr.address1,
        address2=addr.address2,
        city=addr.city,
        state=addr.state,
        zip=addr.zip,
    )


def _to_member_detail(m: MemberModel) -> MemberDetail:
    return MemberDetail(
        memberId=m.member_id,
        subscriberMemberId=m.subscriber_member_id,
        firstName=m.first_name,
        lastName=m.last_name,
        mi=m.mi,
        dateOfBirth=m.date_of_birth,
        age=_calculate_age(m.date_of_birth),
        gender=m.gender,
        ssn=m.ssn,
        phone=m.phone,
        email=m.email,
        languagePreference=m.language_preference,
        insuredId=m.insured_id,
        personCode=m.person_code,
        familyPosition=m.family_position,
        covType=m.cov_type,
        relCode=m.rel_code,
        role=FamilyRole.from_rel_code(m.rel_code),
        lakerPc=m.laker_pc,
        prevCardId=m.prev_card_id,
        startDate=m.start_date,
        endDate=m.end_date,
        status=derive_status(m.start_date, m.end_date),
        plan=_plan_summary(m.plan),
        address=_address_schema(m.address),
    )


def _to_member_summary(m: MemberModel) -> MemberSummary:
    return MemberSummary(
        memberId=m.member_id,
        subscriberMemberId=m.subscriber_member_id,
        firstName=m.first_name,
        lastName=m.last_name,
        mi=m.mi,
        dateOfBirth=m.date_of_birth,
        age=_calculate_age(m.date_of_birth),
        gender=m.gender,
        status=derive_status(m.start_date, m.end_date),
        personCode=m.person_code,
        covType=m.cov_type,
        familyPosition=m.family_position,
        relCode=m.rel_code,
        role=FamilyRole.from_rel_code(m.rel_code),
        insuredId=m.insured_id,
        startDate=m.start_date,
        endDate=m.end_date,
        planId=m.plan_id,
        carrier=m.plan.carrier if m.plan else None,
    )


class MemberService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = MemberRepository(session)
        self._plan_repo = PlanRepository(session)
        self._session = session
        self._cache = CacheService(namespace="member")

    # ── Single member ────────────────────────────────────────────────────────

    async def get_member_by_id(self, member_id: str) -> MemberDetail:
        cached = await self._cache.get(member_id, MemberDetail)
        if cached:
            return cached

        member = await self._repo.get_by_member_id(member_id)
        if not member:
            raise MemberNotFoundException(f"Member '{member_id}' not found.")

        detail = _to_member_detail(member)
        await self._cache.set(member_id, detail)
        return detail

    # ── Search ───────────────────────────────────────────────────────────────

    async def search_members(
        self, request: MemberSearchRequest
    ) -> PagedResponse[MemberSummary]:
        cache_key = self._search_cache_key(request)
        cached = await self._cache.get(cache_key, PagedResponse[MemberSummary])
        if cached:
            return cached

        items, total = await self._repo.search(
            request.searchRequest,
            page=request.pagination.page,
            page_size=request.pagination.page_size,
            sort_by=request.sort.sort_by,
            sort_dir=request.sort.sort_dir,
        )

        if not items:
            raise MemberNotFoundException(
                "No members found matching the search criteria."
            )
        result = PagedResponse.of(
            data=[_to_member_summary(m) for m in items],
            page=request.pagination.page,
            page_size=request.pagination.page_size,
            total=total,
        )
        await self._cache.set(cache_key, result)
        return result

    @staticmethod
    def _search_cache_key(request: MemberSearchRequest) -> str:
        digest = hashlib.sha256(request.model_dump_json().encode()).hexdigest()
        return f"search:{digest}"

    # ── Eligibility ──────────────────────────────────────────────────────────

    async def get_eligibility(self, member_id: str) -> EligibilityResponse:
        """
        Eligibility lives inside Member — this endpoint is a dedicated
        view over the same data for convenience.
        """
        cache_key = f"eligibility:{member_id}"
        cached = await self._cache.get(cache_key, EligibilityResponse)
        if cached:
            return cached

        member = await self._repo.get_by_member_id(member_id)
        if not member:
            raise MemberNotFoundException(f"Member '{member_id}' not found.")
        response = EligibilityResponse(
            memberId=member.member_id,
            status=derive_status(member.start_date, member.end_date),
            startDate=member.start_date,
            endDate=member.end_date,
        )
        await self._cache.set(cache_key, response)
        return response

    # ── Family ───────────────────────────────────────────────────────────────

    async def get_family(
        self,
        member_id: str,
        request: PaginationRequest,
    ) -> PagedResponse[MemberSummary]:
        """
        Return the full family unit for a subscriber.
        member_id must belong to a Cardholder (relCode=01).
        """
        subscriber = await self._repo.get_by_member_id(member_id)
        if not subscriber:
            raise MemberNotFoundException(f"Member '{member_id}' not found.")

        if subscriber.rel_code != RelCode.CARDHOLDER.value:
            raise InvalidFamilyRelationshipException(
                f"Member '{member_id}' is not a Cardholder (relCode=01). "
                "Family can only be retrieved from a subscriber."
            )

        cache_key = (
            f"family:{member_id}:{request.page}:{request.page_size}:"
            f"{request.sort_by}:{request.sort_dir}"
        )
        cached = await self._cache.get(cache_key, PagedResponse[MemberSummary])
        if cached:
            return cached

        items, total = await self._repo.get_family_members(
            member_id,
            page=request.page,
            page_size=request.page_size,
            sort_by=request.sort_by,
            sort_dir=request.sort_dir,
        )
        result = PagedResponse.of(
            data=[_to_member_summary(m) for m in items],
            page=request.page,
            page_size=request.page_size,
            total=total,
        )
        await self._cache.set(cache_key, result)
        return result

    async def add_family_member(
        self,
        subscriber_member_id: str,
        request: AddFamilyMemberRequest,
    ) -> MemberDetail:
        """
        Add a dependent or spouse under an existing Cardholder.

        Business rules enforced:
        1. Subscriber must exist and be a Cardholder (relCode=01).
        2. Only one spouse (relCode=02) is allowed per family.
        3. personCode is backend-generated — never trusted from UI.
        4. Plan (if provided) must exist.
        """
        # 1. Validate subscriber
        subscriber = await self._repo.get_by_member_id(subscriber_member_id)
        if not subscriber:
            raise MemberNotFoundException(
                f"Subscriber '{subscriber_member_id}' not found."
            )
        if subscriber.rel_code != RelCode.CARDHOLDER.value:
            raise InvalidFamilyRelationshipException(
                f"Only a Cardholder (relCode=01) may have dependents added. "
                f"Member '{subscriber_member_id}' has relCode='{subscriber.rel_code}'."
            )

        # 2. Spouse uniqueness check
        if request.rel_code == RelCode.SPOUSE.value:
            spouse_count = await self._repo.get_spouse_count(subscriber_member_id)
            if spouse_count > 0:
                raise DuplicateSpouseException(subscriber_member_id)

        # 3. Validate plan if provided
        if request.plan_id:
            plan = await self._plan_repo.get_by_plan_id(request.plan_id)
            if not plan:
                raise PlanNotFoundException(request.plan_id)

        # 4. Generate person_code
        max_pc = await self._repo.get_max_person_code(subscriber_member_id)
        new_person_code = str(max_pc + 1).zfill(2)

        # 5. Build and persist new member
        new_member_id = MemberRepository.generate_member_id()

        # 6. Generate family_position
        max_fp = await self._repo.get_max_family_position(subscriber_member_id)
        new_family_position = str(max_fp + 1).zfill(2)

        member = MemberModel(
            member_id=new_member_id,
            subscriber_member_id=subscriber_member_id,
            first_name=request.first_name,
            last_name=request.last_name,
            mi=request.mi,
            date_of_birth=request.date_of_birth,
            gender=request.gender,
            ssn=request.ssn,
            phone=request.phone,
            email=str(request.email) if request.email else None,
            language_preference=request.language_preference,
            insured_id=request.insured_id,
            person_code=new_person_code,
            family_position=new_family_position,
            rel_code=request.rel_code,
            laker_pc=request.laker_pc,
            cov_type=request.cov_type,
            prev_card_id=request.prev_card_id,
            start_date=request.start_date,
            end_date=request.end_date,
            plan_id=request.plan_id,
        )

        if request.address:
            member.address = MemberAddressModel(
                address1=request.address.address1,
                address2=request.address.address2,
                city=request.address.city,
                state=request.address.state,
                zip=request.address.zip,
            )

        saved = await self._repo.add(member)
        await self._session.commit()
        await self._session.refresh(saved)

        # Invalidate caches affected by the new member: the subscriber's family
        # listings and any cached search results (the new member may now match).
        await self._cache.delete_pattern(f"family:{subscriber_member_id}:*")
        await self._cache.delete_pattern("search:*")

        return _to_member_detail(saved)
