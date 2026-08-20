from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import SubscobNotFoundException
from app.models.subscob_model import SubscobModel
from app.repositories.subscob_repository import SubscobRepository
from app.schemas.subscob_schema import SubscobInfo


class SubscobService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = SubscobRepository(session)

    def _to_info(self, s: SubscobModel) -> SubscobInfo:
        return SubscobInfo(
            subscriberNum=s.subscriber,
            pc=s.pc,
            lineNum=s.linenum,
            ocFlag=s.ocflag,
            startDate=s.startdt,
            endDate=s.enddt,
            covNote=s.covnote,
            primaryInsuranceId=s.primaryinsuranceid,
        )

    async def list_other_coverage(
        self, subscriber: str, personcode: str
    ) -> list[SubscobInfo]:
        rows = await self._repo.get_by_subscriber(subscriber, personcode)
        if not rows:
            raise SubscobNotFoundException(
                "No other-coverage records found for the given subscriber and "
                "person code."
            )
        return [self._to_info(r) for r in rows]
