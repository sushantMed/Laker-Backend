from __future__ import annotations

from sqlalchemy import select

from app.models.pharmacy_model import PharmacyModel
from app.repositories.base_repository import BaseRepository
from app.schemas.pharmacy_schema import PharmacySearch


class PharmacyRepository(BaseRepository[PharmacyModel]):
    model = PharmacyModel

    async def get_by_nabp(self, nabp: str) -> PharmacyModel | None:
        stmt = select(PharmacyModel).where(
            PharmacyModel.nabp == nabp,
            PharmacyModel.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def search(
        self,
        criteria: PharmacySearch,
        *,
        page: int,
        page_size: int,
        sort_by: str,
        sort_dir: str,
    ) -> tuple[list[PharmacyModel], int]:
        stmt = select(PharmacyModel).where(PharmacyModel.is_deleted.is_(False))

        if criteria.name:
            stmt = stmt.where(PharmacyModel.pharmacy_name.ilike(f"%{criteria.name}%"))
        if criteria.nabp:
            stmt = stmt.where(PharmacyModel.nabp.ilike(f"%{criteria.nabp}%"))
        if criteria.npi:
            stmt = stmt.where(PharmacyModel.npi.ilike(f"%{criteria.npi}%"))
        if criteria.city:
            stmt = stmt.where(PharmacyModel.city.ilike(f"%{criteria.city}%"))
        if criteria.state:
            stmt = stmt.where(PharmacyModel.state.ilike(criteria.state))
        if criteria.zip_code:
            stmt = stmt.where(PharmacyModel.zip.ilike(f"{criteria.zip_code}%"))
        if criteria.is_24_hour is not None:
            stmt = stmt.where(PharmacyModel.is_24_hour.is_(criteria.is_24_hour))
        if criteria.in_network is not None:
            stmt = stmt.where(PharmacyModel.in_network.is_(criteria.in_network))

        return await self.paginate(
            stmt,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
