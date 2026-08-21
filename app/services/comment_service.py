from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subs_notes_model import SubsNotesModel
from app.repositories.subs_notes_repository import SubsNotesRepository
from app.schemas.comment_schema import CommentInfo


class CommentService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = SubsNotesRepository(session)

    def _to_info(self, n: SubsNotesModel) -> CommentInfo:
        return CommentInfo(
            subscriberNum=n.subscriber,
            pc=n.pc,
            lineNum=n.linenum,
            user=n.name,
            date=n.dt,
            note=n.note,
        )

    async def list_comments(
        self, subscriber: str, personcode: str
    ) -> list[CommentInfo]:
        rows = await self._repo.get_by_subscriber(subscriber, personcode)
        return [self._to_info(r) for r in rows]
