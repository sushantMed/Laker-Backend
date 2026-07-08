"""
Member repository.

All queries explicitly exclude soft-deleted rows (is_deleted=False).
Plan is joined via MemberModel.plan relationship (lazy="joined" on model),
so carrier filter can use the join directly.
"""

from __future__ import annotations

import time

from sqlalchemy import select, func
from datetime import date as date_type

from app.models.member_model import MemberModel
from app.models.plan_model import PlanModel
from app.repositories.base_repository import BaseRepository
from app.schemas.member_schema import MemberSearch


class MemberRepository(BaseRepository[MemberModel]):
    model = MemberModel

    # ── Single lookup ────────────────────────────────────────────────────────

    async def get_by_member_id(self, member_id: str) -> MemberModel | None:
        """Fetch one member with address and plan eager-loaded."""
        stmt = select(MemberModel).where(
            MemberModel.member_id.ilike(member_id),
            MemberModel.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    # ── Search ───────────────────────────────────────────────────────────────

    async def search(
        self,
        criteria: MemberSearch,
        *,
        page: int,
        page_size: int,
        sort_by: str,
        sort_dir: str,
    ) -> tuple[list[MemberModel], int]:
        stmt = (
            select(MemberModel)
            .join(MemberModel.plan, isouter=True)
            .where(MemberModel.is_deleted.is_(False))
        )

        # Include Termed Members checkbox
        # Default: only ACTIVE and PENDING. When checked: include INACTIVE too.
        if not criteria.include_termed_members:
            today = date_type.today()
            stmt = stmt.where(MemberModel.end_date >= today)

        if criteria.carrier:
            stmt = stmt.where(PlanModel.carrier.ilike(f"%{criteria.carrier}%"))
        if criteria.member_id:
            # Search By Previous Card ID checkbox
            if criteria.search_by_prev_card_id:
                stmt = stmt.where(
                    MemberModel.prev_card_id.ilike(f"%{criteria.member_id}%")
                )
            else:
                stmt = stmt.where(MemberModel.member_id.ilike(f"{criteria.member_id}%"))

        if criteria.first_name:
            stmt = stmt.where(MemberModel.first_name.ilike(f"%{criteria.first_name}%"))
        if criteria.last_name:
            stmt = stmt.where(MemberModel.last_name.ilike(f"%{criteria.last_name}%"))
        if criteria.mi:
            stmt = stmt.where(MemberModel.mi.ilike(f"{criteria.mi}%"))
        if criteria.date_of_birth:
            stmt = stmt.where(MemberModel.date_of_birth == criteria.date_of_birth)

        return await self.paginate(
            stmt,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )

    # ── Family ───────────────────────────────────────────────────────────────

    async def get_family_members(
        self,
        subscriber_member_id: str,
        *,
        page: int,
        page_size: int,
        sort_by: str,
        sort_dir: str,
    ) -> tuple[list[MemberModel], int]:
        stmt = (
            select(MemberModel)
            .join(MemberModel.plan, isouter=True)
            .where(
                MemberModel.is_deleted.is_(False),
                (
                    (MemberModel.subscriber_member_id == subscriber_member_id)
                    | (MemberModel.member_id == subscriber_member_id)
                ),
            )
        )

        return await self.paginate(
            stmt,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )

    async def get_spouse_count(self, subscriber_member_id: str) -> int:
        """Count existing spouses (relCode=02) under a subscriber."""
        stmt = select(func.count()).where(
            MemberModel.subscriber_member_id == subscriber_member_id,
            MemberModel.rel_code == "02",
            MemberModel.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_max_person_code(self, subscriber_member_id: str) -> int:
        """
        Return the numeric value of the highest personCode currently assigned
        in this family so the service can increment and assign the next one.
        """
        # Include the subscriber themselves (who has no subscriber_member_id)
        stmt = select(func.max(MemberModel.person_code)).where(
            MemberModel.is_deleted.is_(False),
            (
                (MemberModel.subscriber_member_id == subscriber_member_id)
                | (MemberModel.member_id == subscriber_member_id)
            ),
        )
        result = await self.session.execute(stmt)
        raw = result.scalar_one_or_none()
        if raw is None:
            return 0
        try:
            return int(raw)
        except (ValueError, TypeError):
            return 0

    async def get_max_family_position(self, subscriber_member_id: str) -> int:

        stmt = select(func.max(MemberModel.family_position)).where(
            MemberModel.is_deleted.is_(False),
            (
                (MemberModel.subscriber_member_id == subscriber_member_id)
                | (MemberModel.member_id == subscriber_member_id)
            ),
        )

        result = await self.session.execute(stmt)
        raw = result.scalar_one_or_none()
        if raw is None:
         return 0
        try:
           return int(raw)
        except (ValueError, TypeError):
           return 0

    # ── Persistence ──────────────────────────────────────────────────────────

    async def add(self, member: MemberModel) -> MemberModel:
        self.session.add(member)
        await self.session.flush()  # get DB-generated fields without committing
        await self.session.refresh(member)
        return member

    @staticmethod
    def generate_member_id() -> str:
        """Generate a unique member_id. In production, replace with
        a sequence or domain-specific algorithm."""
        suffix = str(int(time.time() * 1000))[-3:]
        return f"MBR{suffix}"


