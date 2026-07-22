"""
Claim repository.

Data-access layer only — no business rules here (that's ClaimService's job).
Mirrors MemberRepository's shape: plain async methods returning ORM models
or (items, total) tuples for paged queries.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import asc, desc, false, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.claim_model import ClaimModel

_SORTABLE_COLUMNS = {
    "authNum": ClaimModel.auth_num,
    "dateFilled": ClaimModel.date_filled,
    "memberId": ClaimModel.member_id,
    "rxNumber": ClaimModel.rx_number,
    "drug": ClaimModel.drug_name,
    "ndc": ClaimModel.ndc,
}
_DEFAULT_SORT_COLUMN = ClaimModel.date_filled


class ClaimRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Lookups ──────────────────────────────────────────────────────────────

    async def get_by_auth_num(self, auth_num: str) -> ClaimModel | None:
        stmt = (
            select(ClaimModel)
            .options(joinedload(ClaimModel.member))
            .where(ClaimModel.auth_num.ilike(auth_num))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ── Search ───────────────────────────────────────────────────────────────

    async def search(
        self,
        member_id: str | None = None,
        auth_num: str | None = None,
        date_filled_start: date | None = None,
        date_filled_end: date | None = None,
        exclude_test_claims: bool = True,
        page: int = 1,
        page_size: int = 10,
        sort_by: str | None = None,
        sort_dir: str = "asc",
    ) -> tuple[Sequence[ClaimModel], int]:
        stmt = select(ClaimModel).options(joinedload(ClaimModel.member))
        if member_id:
            stmt = stmt.where(ClaimModel.member_id.ilike(member_id))
        if auth_num:
            stmt = stmt.where(ClaimModel.auth_num.ilike(auth_num))
        if date_filled_start:
            stmt = stmt.where(ClaimModel.date_filled >= date_filled_start)
        if date_filled_end:
            stmt = stmt.where(ClaimModel.date_filled <= date_filled_end)
        if exclude_test_claims:
            stmt = stmt.where(ClaimModel.is_test_claim == false())

        return await self._paginate(stmt, page, page_size, sort_by, sort_dir)

    # ── Claims for a member ──────────────────────────────────────────────────

    async def get_claims_by_member_id(
        self,
        member_id: str,
        exclude_test_claims: bool = True,
        page: int = 1,
        page_size: int = 10,
        sort_by: str | None = None,
        sort_dir: str = "asc",
    ) -> tuple[Sequence[ClaimModel], int]:
        stmt = (
            select(ClaimModel)
            .options(joinedload(ClaimModel.member))
            .where(ClaimModel.member_id.ilike(member_id))
        )
        if exclude_test_claims:
            stmt = stmt.where(ClaimModel.is_test_claim == false())

        return await self._paginate(stmt, page, page_size, sort_by, sort_dir)

    # ── Claims for a pharmacy / prescriber / drug ───────────────────────────

    async def get_claims_by_pharmacy_nabp(
        self,
        nabp: str,
        date_filled_start: date | None = None,
        date_filled_end: date | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[Sequence[ClaimModel], int]:
        stmt = (
            select(ClaimModel)
            .options(joinedload(ClaimModel.member))
            .where(ClaimModel.pharmacy_nabp == nabp)
        )
        stmt = self._apply_date_range(stmt, date_filled_start, date_filled_end)
        return await self._paginate(stmt, page, page_size, None, "desc")

    async def get_claims_by_prescriber_npi(
        self,
        npi: str,
        date_filled_start: date | None = None,
        date_filled_end: date | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[Sequence[ClaimModel], int]:
        stmt = (
            select(ClaimModel)
            .options(joinedload(ClaimModel.member))
            .where(ClaimModel.prescriber_npi == npi)
        )
        stmt = self._apply_date_range(stmt, date_filled_start, date_filled_end)
        return await self._paginate(stmt, page, page_size, None, "desc")

    async def get_claims_by_drug_ndc(
        self,
        ndc: str,
        date_filled_start: date | None = None,
        date_filled_end: date | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[Sequence[ClaimModel], int]:
        stmt = (
            select(ClaimModel)
            .options(joinedload(ClaimModel.member))
            .where(ClaimModel.ndc == ndc)
        )
        stmt = self._apply_date_range(stmt, date_filled_start, date_filled_end)
        return await self._paginate(stmt, page, page_size, None, "desc")

    # ── Mutations ────────────────────────────────────────────────────────────

    async def add(self, claim: ClaimModel) -> ClaimModel:
        self._session.add(claim)
        await self._session.flush()
        return claim

    @staticmethod
    def generate_claim_id() -> str:
        return str(uuid.uuid4())

    # ── Internal helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _apply_date_range(
        stmt,
        date_filled_start: date | None,
        date_filled_end: date | None,
    ):
        if date_filled_start:
            stmt = stmt.where(ClaimModel.date_filled >= date_filled_start)
        if date_filled_end:
            stmt = stmt.where(ClaimModel.date_filled <= date_filled_end)
        return stmt

    async def _paginate(
        self,
        stmt,
        page: int,
        page_size: int,
        sort_by: str | None,
        sort_dir: str,
    ) -> tuple[Sequence[ClaimModel], int]:
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        sort_column = _SORTABLE_COLUMNS.get(sort_by, _DEFAULT_SORT_COLUMN)
        order_fn = desc if sort_dir == "desc" else asc
        stmt = stmt.order_by(order_fn(sort_column))

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(stmt)
        items = result.unique().scalars().all()
        return items, total
