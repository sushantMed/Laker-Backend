from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    model: type[ModelType]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def paginate(
        self,
        stmt,
        *,
        page: int,
        page_size: int,
        sort_by: str,
        sort_dir: str,
    ) -> tuple[list[ModelType], int]:
        """
        Apply ORDER BY, COUNT, LIMIT, OFFSET to any SELECT statement.
        Returns (items, total_count).
        """
        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        # Sort
        column = getattr(self.model, sort_by, None)
        if column is not None:
            from sqlalchemy import asc, desc

            order_fn = desc if sort_dir.upper() == "DESC" else asc
            stmt = stmt.order_by(order_fn(column))

        # Page
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        items = list((await self.session.execute(stmt)).scalars().all())

        return items, total
