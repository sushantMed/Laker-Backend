from __future__ import annotations

from sqlalchemy import select

from app.models.prescriber_model import PrescriberModel
from app.repositories.base_repository import BaseRepository
from app.schemas.prescriber_schema import PrescriberSearch


class PrescriberRepository(BaseRepository[PrescriberModel]):
    model = PrescriberModel

    async def get_by_npi(self, npi: str) -> PrescriberModel | None:
        stmt = select(PrescriberModel).where(
            PrescriberModel.npi == npi,
            PrescriberModel.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def search(
        self,
        criteria: PrescriberSearch,
        *,
        page: int,
        page_size: int,
        sort_by: str,
        sort_dir: str,
    ) -> tuple[list[PrescriberModel], int]:
        stmt = select(PrescriberModel).where(PrescriberModel.is_deleted.is_(False))

        if criteria.name:
            stmt = stmt.where(PrescriberModel.name.ilike(f"%{criteria.name}%"))
        if criteria.npi:
            stmt = stmt.where(PrescriberModel.npi.ilike(f"%{criteria.npi}%"))
        if criteria.dea:
            stmt = stmt.where(PrescriberModel.dea.ilike(f"%{criteria.dea}%"))
        if criteria.specialty:
            stmt = stmt.where(PrescriberModel.specialty.ilike(f"%{criteria.specialty}%"))
        if criteria.city:
            stmt = stmt.where(PrescriberModel.city.ilike(f"%{criteria.city}%"))
        if criteria.state:
            stmt = stmt.where(PrescriberModel.state.ilike(criteria.state))

        return await self.paginate(
            stmt,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
