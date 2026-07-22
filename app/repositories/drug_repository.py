from __future__ import annotations

from sqlalchemy import false, select

from app.models.drug_model import DrugModel
from app.repositories.base_repository import BaseRepository
from app.schemas.drug_schema import DrugSearch


class DrugRepository(BaseRepository[DrugModel]):
    model = DrugModel

    async def get_by_ndc(self, ndc: str) -> DrugModel | None:
        stmt = select(DrugModel).where(
            DrugModel.ndc == ndc,
            DrugModel.is_deleted == false(),
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_gpi(
        self,
        gpi: str,
        *,
        page: int,
        page_size: int,
        sort_by: str,
        sort_dir: str,
    ) -> tuple[list[DrugModel], int]:
        stmt = select(DrugModel).where(
            DrugModel.gpi == gpi,
            DrugModel.is_deleted == false(),
        )
        return await self.paginate(
            stmt,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )

    async def search(
        self,
        criteria: DrugSearch,
        *,
        page: int,
        page_size: int,
        sort_by: str,
        sort_dir: str,
    ) -> tuple[list[DrugModel], int]:
        stmt = select(DrugModel).where(DrugModel.is_deleted == false())

        if criteria.name:
            stmt = stmt.where(DrugModel.drug_name.ilike(f"%{criteria.name}%"))
        if criteria.ndc:
            stmt = stmt.where(DrugModel.ndc.ilike(f"%{criteria.ndc}%"))
        if criteria.gpi:
            stmt = stmt.where(DrugModel.gpi.ilike(f"%{criteria.gpi}%"))
        if criteria.brand_generic:
            if criteria.brand_generic == "ALL":
                stmt = stmt.where(DrugModel.brand_generic.in_(["BRAND", "GENERIC"]))
            else:
                stmt = stmt.where(DrugModel.brand_generic == criteria.brand_generic)
        if criteria.maintenance:
            stmt = stmt.where(DrugModel.maintenance == criteria.maintenance)
        if criteria.tier or criteria.tier == 0:
            if criteria.tier == 0:  # include all from 1 to 4
                stmt = stmt.where(DrugModel.tier.in_([1, 2, 3, 4]))
            else:
                stmt = stmt.where(DrugModel.tier == criteria.tier)

        return await self.paginate(
            stmt,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
