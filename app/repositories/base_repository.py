import re
from typing import Generic, TypeVar

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import ColumnProperty

from app.database.base import Base

ModelType = TypeVar("ModelType", bound=Base)

_CAMEL_TO_SNAKE = re.compile(r"(?<!^)(?=[A-Z])")


def _to_snake_case(name: str) -> str:
    """Convert an API-facing camelCase sort key to a model snake_case attribute.

    e.g. "lastName" -> "last_name", "dateOfBirth" -> "date_of_birth".
    Values already in snake_case (or single words) pass through unchanged.
    """
    return _CAMEL_TO_SNAKE.sub("_", name).lower()


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
        # The API surface is camelCase (e.g. "lastName") while model columns are
        # snake_case ("last_name"), so normalize before resolving the attribute.
        # Only accept real mapped columns; fall back to the primary key so
        # pagination is always deterministic instead of silently unordered.
        column = getattr(self.model, _to_snake_case(sort_by), None)
        if not isinstance(getattr(column, "property", None), ColumnProperty):
            column = self.model.id

        order_fn = desc if sort_dir.upper() == "DESC" else asc
        stmt = stmt.order_by(order_fn(column))

        # Page
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        items = list((await self.session.execute(stmt)).scalars().all())

        return items, total
