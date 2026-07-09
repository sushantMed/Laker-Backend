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
from app.cache.cache_service import CacheService
from app.utils.pagination import PaginationRequest

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ClaimNotFoundException,
    DrugNotFoundException,
    MemberNotFoundException,
    PharmacyNotFoundException,
    PrescriberNotFoundException,
)
from app.models.claim_model import ClaimModel
from app.repositories.claim_repository import ClaimRepository
from app.repositories.member_repository import MemberRepository

from app.repositories.pharmacy_repository import PharmacyRepository
from app.repositories.prescriber_repository import PrescriberRepository
from app.repositories.drug_repository import DrugRepository

from app.schemas.claim_schema import (
    ClaimDetail,
    ClaimSearchRequest,
    ClaimsByEntityQuery,
    ClaimSummary,
    PharmacySummary,
    PrescriberSummary,
)
from app.utils.pagination import PagedResponse


def _to_claim_summary(c: ClaimModel) -> ClaimSummary:
    return ClaimSummary(
        authNum=c.auth_num,
        dateFilled=c.date_filled,
        memberId=c.member_id,
        firstName=c.member.first_name if c.member else None,
        lastName=c.member.last_name if c.member else None,
        rxNumber=c.rx_number,
        drug=c.drug_name,
        ndc=c.ndc,
        isTestClaim=c.is_test_claim,
    )


def _to_claim_detail(c: ClaimModel) -> ClaimDetail:
    return ClaimDetail(
        claimId=c.claim_id,
        authNum=c.auth_num,
        memberId=c.member_id,
        firstName=c.member.first_name if c.member else None,
        lastName=c.member.last_name if c.member else None,
        rxNumber=c.rx_number,
        drug=c.drug_name,
        ndc=c.ndc,
        dateFilled=c.date_filled,
        dateWritten=c.date_written,
        quantity=c.quantity,
        daysSupply=c.days_supply,
        refillsRemaining=c.refills_remaining,
        pharmacy=(
            PharmacySummary(
                pharmacyNpi=c.pharmacy_npi,
                pharmacyName=c.pharmacy_name,
            )
            if c.pharmacy_npi or c.pharmacy_name
            else None
        ),
        prescriber=(
            PrescriberSummary(
                prescriberNpi=c.prescriber_npi,
                prescriberName=c.prescriber_name,
            )
            if c.prescriber_npi or c.prescriber_name
            else None
        ),
        ingredientCost=c.ingredient_cost,
        dispensingFee=c.dispensing_fee,
        copay=c.copay,
        totalPaid=c.total_paid,
        isTestClaim=c.is_test_claim,
        planId=c.plan_id,
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
            raise ClaimNotFoundException(
                f"Claim with auth num '{auth_num}' not found."
            )

        detail = _to_claim_detail(claim)
        await self._cache.set(auth_num, detail)
        return detail

    # ── C1: Search ───────────────────────────────────────────────────────────

    async def search_claims(
        self, request: ClaimSearchRequest
    ) -> PagedResponse[ClaimSummary]:
        """
        Search claims by Member ID and / or Auth Num, optionally narrowed
        by a Date Filled range. Test claims are excluded by default.

        Search-criteria validation (at least one criterion; date range
        required if memberId absent; max 12-month range) is enforced by
        ClaimSearch's model_validators, not repeated here.
        """
        criteria = request.searchRequest

        items, total = await self._repo.search(
            member_id=criteria.member_id,
            auth_num=criteria.auth_num,
            date_filled_start=criteria.date_filled_start,
            date_filled_end=criteria.date_filled_end,
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
        self, member_id: str, request: ClaimSearchRequest
    ) -> PagedResponse[ClaimSummary]:
        """
        Same underlying query as C1, but memberId is taken from the path
        and overrides whatever (if anything) was sent in the request body.
        Validates the member exists first -> 404 MemberNotFound.
        """
        member = await self._member_repo.get_by_member_id(member_id)
        if not member:
            raise MemberNotFoundException(f"Member '{member_id}' not found.")

        criteria = request.searchRequest

        items, total = await self._repo.search(
            member_id=member_id,  # path param takes precedence over body
            auth_num=criteria.auth_num,
            date_filled_start=criteria.date_filled_start,
            date_filled_end=criteria.date_filled_end,
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


    async def get_claims_for_member(
        self,
        member_id: str,
        request: PaginationRequest,
        exclude_test_claims: bool = True,
    ) -> PagedResponse[ClaimSummary]:
        """
        Return the claim history for a single member.
        Validates the member exists before querying claims, mirroring
        the subscriber check used when pulling a family unit.
        """
        member = await self._member_repo.get_by_member_id(member_id)
        if not member:
            return PagedResponse.of(
                data=[],
                page=request.page,
                page_size=request.page_size,
                total=0,
            )

        items, total = await self._repo.get_claims_by_member_id(
            member_id,
            exclude_test_claims=exclude_test_claims,
            page=request.page,
            page_size=request.page_size,
        )
        return PagedResponse.of(
            data=[_to_claim_summary(c) for c in items],
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
            date_filled_start=query.start_date,
            date_filled_end=query.end_date,
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
            date_filled_start=query.start_date,
            date_filled_end=query.end_date,
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
            date_filled_start=query.start_date,
            date_filled_end=query.end_date,
            page=query.page,
            page_size=query.page_size,
        )
        return PagedResponse.of(
            data=[_to_claim_summary(c) for c in items],
            page=query.page,
            page_size=query.page_size,
            total=total,
        )
