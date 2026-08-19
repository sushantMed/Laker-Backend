from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import SubscriberEligibilityNotFoundException
from app.models.subscriber_elig_list_model import SubscriberEligListModel
from app.repositories.subscriber_elig_list_repository import (
    SubscriberEligListRepository,
)
from app.schemas.subscriber_elig_list_schema import (
    SubscriberEligibilityInfo,
    SubscriberEligibilityLookupRequest,
)


class SubscriberEligListService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = SubscriberEligListRepository(session)

    def _to_info(self, e: SubscriberEligListModel) -> SubscriberEligibilityInfo:
        return SubscriberEligibilityInfo(
            subscriber=e.subscriber,
            personCode=e.personcode,
            clientCode=e.clientcode,
            lineNum=e.linenum,
            startDate=e.startdt,
            endDate=e.enddt,
            changeDate=e.changedt,
        )

    async def get_subscriber_eligibility(
        self, request: SubscriberEligibilityLookupRequest
    ) -> list[SubscriberEligibilityInfo]:
        if request.as_of_date is not None:
            records = await self._repo.get_active_eligibility(
                request.subscriber,
                request.personcode,
                request.clientcode,
                request.as_of_date,
            )
        else:
            records = await self._repo.get_by_subscriber(
                request.subscriber, request.personcode, request.clientcode
            )

        if not records:
            raise SubscriberEligibilityNotFoundException(
                "No subscriber eligibility found for the given subscriber, "
                "person code, and client code."
            )

        return [self._to_info(e) for e in records]
