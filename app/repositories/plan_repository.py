from sqlalchemy import select, false

from app.models.plan_model import PlanModel
from app.repositories.base_repository import BaseRepository


class PlanRepository(BaseRepository[PlanModel]):
    model = PlanModel

    async def get_by_plan_id(self, plan_id: str) -> PlanModel | None:
        stmt = select(PlanModel).where(
            PlanModel.plan_id == plan_id,
            PlanModel.is_deleted == false(),
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
