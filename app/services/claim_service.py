"""
Claim service.

Business logic layer.  Only raises LakerBaseException subclasses —
never ValueError or bare Exception.
HTTP status mapping is the controller's responsibility.

NOTE on empty results: per the API spec, only GET /claims/{authNum} (C2)
returns 404 ClaimNotFound. The search/list endpoints (C1, C3-C7) return an
empty PagedResponse when nothing matches -- they do NOT raise
ClaimNotFoundException, since "no results" is a valid, expected outcome for
a search and isn't listed as an error response for those routes.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.cache_service import CacheService
from app.core.config import settings
from app.core.exceptions import (
    ClaimNotFoundException,
    DrugNotFoundException,
    MemberNotFoundException,
    PharmacyNotFoundException,
    PrescriberNotFoundException,
)
from app.models.claim_model import ClaimModel
from app.repositories.claim_repository import ClaimRepository
from app.repositories.drug_repository import DrugRepository
from app.repositories.member_repository import MemberRepository
from app.repositories.pharmacy_repository import PharmacyRepository
from app.repositories.prescriber_repository import PrescriberRepository
from app.schemas.claim_schema import (
    ClaimDetail,
    ClaimsByEntityQuery,
    ClaimSearchByMemberRequest,
    ClaimSearchRequest,
    ClaimSummary,
    PharmacySummary,
    PrescriberSummary,
)
from app.utils.pagination import PagedResponse


def _to_claim_summary(c: ClaimModel) -> ClaimSummary:
    return ClaimSummary(
        auth_num=c.auth_num,
        date_filled=c.date_filled,
        member_id=c.member_id,
        first_name=c.member.first_name if c.member else None,
        last_name=c.member.last_name if c.member else None,
        rx_number=c.rx_number,
        drug=c.drug_name,
        ndc=c.ndc,
        is_test_claim=c.is_test_claim,
    )


def _to_claim_detail(c: ClaimModel) -> ClaimDetail:
    return ClaimDetail(
        claim_id=c.claim_id,
        auth_num=c.auth_num,
        member_id=c.member_id,
        first_name=c.member.first_name if c.member else None,
        last_name=c.member.last_name if c.member else None,
        rx_number=c.rx_number,
        drug=c.drug_name,
        ndc=c.ndc,
        date_filled=c.date_filled,
        quantity=c.quantity,
        days_supply=c.days_supply,
        refills_remaining=c.refills_remaining,
        pharmacy=(
            PharmacySummary(
                pharmacy_npi=c.pharmacy_npi,
                pharmacy_name=c.pharmacy_name,
            )
            if c.pharmacy_npi or c.pharmacy_name
            else None
        ),
        prescriber=(
            PrescriberSummary(
                prescriber_npi=c.prescriber_npi,
                prescriber_name=c.prescriber_name,
            )
            if c.prescriber_npi or c.prescriber_name
            else None
        ),
        ingredient_cost=c.ingredient_cost,
        dispensing_fee=c.dispensing_fee,
        copay=c.copay,
        total_paid=c.total_paid,
        is_test_claim=c.is_test_claim,
        plan_id=c.plan_id,
    )


class ClaimService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ClaimRepository(session)
        self._member_repo = MemberRepository(session)
        self._pharmacy_repo = PharmacyRepository(session)
        self._prescriber_repo = PrescriberRepository(session)
        self._drug_repo = DrugRepository(session)
        self._session = session
        self._cache = CacheService(namespace="claim")

    # ── C2: Single claim ────────────────────────────────────────────────────

    async def get_claim_by_auth_num(self, auth_num: str) -> ClaimDetail:
        cached = await self._cache.get(auth_num, ClaimDetail)
        if cached:
            return cached

        claim = await self._repo.get_by_auth_num(auth_num)
        if not claim:
            raise ClaimNotFoundException(f"Claim with auth num '{auth_num}' not found.")

        detail = _to_claim_detail(claim)
        await self._cache.set(auth_num, detail)
        return detail

    # ── C1: Search ───────────────────────────────────────────────────────────

    async def search_claims(
        self, request: ClaimSearchRequest
    ) -> PagedResponse[ClaimSummary]:
        """
        Search claims by Member ID and / or Auth Num, optionally narrowed
        by a Date Filled cutoff. Test claims are excluded by default.

        Search-criteria validation (at least one criterion; dateFilled
        required if memberId absent) is enforced by ClaimSearch's
        model_validators.
        """
        criteria = request.searchRequest

        items, total = await self._repo.search(
            member_id=criteria.member_id,
            auth_num=criteria.auth_num,
            date_filled=criteria.date_filled,
            exclude_test_claims=criteria.exclude_test_claims,
            page=request.pagination.page,
            page_size=request.pagination.page_size,
            sort_by=request.sort.sort_by,
            sort_dir=request.sort.sort_dir,
        )

        return PagedResponse.of(
            data=[_to_claim_summary(c) for c in items],
            page=request.pagination.page,
            page_size=request.pagination.page_size,
            total=total,
        )

    async def search_claims_for_member(
        self,
        member_id: str,
        request: ClaimSearchByMemberRequest,
        page: int,
        page_size: int,
    ) -> PagedResponse[ClaimDetail]:
        """
        Same underlying query as C1, but memberId is taken from the path.
        Validates the member exists first -> 404 MemberNotFound.

        When `recent` is true, the trailing `recent_claims_window_days`
        window is computed here (not exposed as a request field) and used
        as the lower bound of the dateFilled search.

        Results are sorted by dateFilled descending, most recent first.
        """
        member = await self._member_repo.get_by_member_id(member_id)
        if not member:
            raise MemberNotFoundException(f"Member '{member_id}' not found.")

        date_filled = request.date_filled
        date_filled_from = None
        if request.recent:
            date_filled_from = date.today() - timedelta(
                days=settings.recent_claims_window_days
            )
            date_filled = date.today()

        items, total = await self._repo.search(
            member_id=member_id,
            auth_num=request.auth_num,
            date_filled=date_filled,
            date_filled_from=date_filled_from,
            exclude_test_claims=request.exclude_test_claims,
            page=page,
            page_size=page_size,
            sort_by="dateFilled",
            sort_dir="desc",
        )

        return PagedResponse.of(
            data=[_to_claim_detail(c) for c in items],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def get_claims_for_member[T](
        self,
        member_id: str,
        request: ClaimsByEntityQuery,
        transform: Callable[[ClaimModel], T],
        exclude_test_claims: bool = True,
        sort_by: str | None = None,
        sort_dir: str = "asc",
    ) -> PagedResponse[T]:
        """
        Return claims for a member.

        The caller provides a mapper that converts each ClaimModel into the
        desired response DTO (e.g. ClaimSummary, ClaimDetail).
        """

        member = await self._member_repo.get_by_member_id(member_id)
        if not member:
            raise MemberNotFoundException(f"Member '{member_id}' not found.")

        items, total = await self._repo.get_claims_by_member_id(
            member_id=member_id,
            exclude_test_claims=exclude_test_claims,
            date_filled=request.end_date,
            page=request.page,
            page_size=request.page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )

        return PagedResponse.of(
            data=[transform(item) for item in items],
            page=request.page,
            page_size=request.page_size,
            total=total,
        )

    async def get_claims_for_pharmacy(
        self, nabp: str, query: ClaimsByEntityQuery
    ) -> PagedResponse[ClaimSummary]:
        pharmacy = await self._pharmacy_repo.get_by_nabp(nabp)
        if not pharmacy:
            raise PharmacyNotFoundException(f"Pharmacy '{nabp}' not found.")

        items, total = await self._repo.get_claims_by_pharmacy_nabp(
            nabp,
            date_filled=query.end_date,
            page=query.page,
            page_size=query.page_size,
        )
        return PagedResponse.of(
            data=[_to_claim_summary(c) for c in items],
            page=query.page,
            page_size=query.page_size,
            total=total,
        )

    async def get_claims_for_prescriber(
        self, npi: str, query: ClaimsByEntityQuery
    ) -> PagedResponse[ClaimSummary]:
        prescriber = await self._prescriber_repo.get_by_npi(npi)
        if not prescriber:
            raise PrescriberNotFoundException(f"Prescriber '{npi}' not found.")

        items, total = await self._repo.get_claims_by_prescriber_npi(
            npi,
            date_filled=query.end_date,
            page=query.page,
            page_size=query.page_size,
        )
        return PagedResponse.of(
            data=[_to_claim_summary(c) for c in items],
            page=query.page,
            page_size=query.page_size,
            total=total,
        )

    async def get_claims_for_drug(
        self, ndc: str, query: ClaimsByEntityQuery
    ) -> PagedResponse[ClaimSummary]:
        drug = await self._drug_repo.get_by_ndc(ndc)
        if not drug:
            raise DrugNotFoundException(f"Drug with NDC '{ndc}' not found.")

        items, total = await self._repo.get_claims_by_drug_ndc(
            ndc,
            date_filled=query.end_date,
            page=query.page,
            page_size=query.page_size,
        )
        return PagedResponse.of(
            data=[_to_claim_summary(c) for c in items],
            page=query.page,
            page_size=query.page_size,
            total=total,
        )
