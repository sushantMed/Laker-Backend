from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    EligibilityDateOverlapException,
    InvalidEligibilityDataException,
    SubscriberGroupNotFoundException,
    SubscriberNotFoundException,
)
from app.models.member_model import Subscriber
from app.models.subscriber_group_list_model import SubscriberGroupListModel
from app.repositories.groups_repository import GroupsRepository
from app.repositories.subscriber_group_list_repository import (
    SubscriberGroupListRepository,
)
from app.repositories.subscriber_repository import SubscriberRepository
from app.schemas.subscriber_group_list_schema import (
    EligibilityCreate,
    EligibilityUpdate,
    SubscriberGroupInfo,
    SubscriberGroupLookupRequest,
)

# Every legacy GetPatientInformation() query hardcodes `AND sub.clientcode = 'YYY'` --
# there is no per-request clientcode in this system today, so it's fixed here too.
DEFAULT_CLIENTCODE = "YYY"

# Only the primary cardholder may add/edit their own group-eligibility rows
# (mirrors btnAddGroupLineLocal.Visible gating on PersonCode = "01").
CARDHOLDER_PERSON_CODE = "01"

# GROUPS.BITFLAGS2 bit that forces COVTYPE='I' (cardholder-only, blocks dependents).
GROUPS_CARDHOLDER_ONLY_BIT = 512

_MAX_DATE = date.max


def _ranges_overlap(
    start1: date, end1: date | None, start2: date, end2: date | None
) -> bool:
    end1 = end1 or _MAX_DATE
    end2 = end2 or _MAX_DATE
    return start1 <= end2 and start2 <= end1


class SubscriberGroupListService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = SubscriberGroupListRepository(session)
        self._subscriber_repo = SubscriberRepository(session)
        self._groups_repo = GroupsRepository(session)

    def _to_info(self, g: SubscriberGroupListModel) -> SubscriberGroupInfo:
        return SubscriberGroupInfo(
            subscriberNum=g.subscriber,
            lineNum=g.linenum,
            groupNum=g.groupnum,
            startDate=g.startdt,
            endDate=g.enddt,
            coverageType=g.covtype,
        )

    async def get_subscriber_groups(
        self, request: SubscriberGroupLookupRequest
    ) -> list[SubscriberGroupInfo]:
        if request.as_of_date is not None:
            groups = await self._repo.get_active_groups(
                request.subscriber, request.clientcode, request.as_of_date
            )
        else:
            groups = await self._repo.get_by_subscriber(
                request.subscriber, request.clientcode
            )

        if not groups:
            raise SubscriberGroupNotFoundException(
                "No subscriber group found for the given subscriber and client code."
            )

        return [self._to_info(g) for g in groups]

    async def _require_subscriber(self, subscribernum: str) -> Subscriber:
        """Validate the subscribernum against the legacy SUBSCRIBER table.

        Group-eligibility rows are cardholder-level (SUBSCRIBERGROUPLIST.SUBSCRIBER
        is the cardholder's subscribernum), so the lookup is always pinned to the
        cardholder's own record (person code 01).
        """
        subscriber = await self._subscriber_repo.get_by_subscribernum(
            subscribernum, CARDHOLDER_PERSON_CODE, DEFAULT_CLIENTCODE
        )
        if subscriber is None:
            raise SubscriberNotFoundException(
                f"Subscriber '{subscribernum}' not found."
            )
        return subscriber

    async def _resolve_covtype(
        self, groupnum: str, requested_covtype: str | None
    ) -> str | None:
        group = await self._groups_repo.get_by_groupnum(groupnum)
        is_cardholder_only = (
            group is not None
            and group.bitflags2 is not None
            and int(group.bitflags2) & GROUPS_CARDHOLDER_ONLY_BIT
        )
        if is_cardholder_only:
            if requested_covtype not in (None, "I"):
                raise InvalidEligibilityDataException(
                    f"Group '{groupnum}' is restricted to cardholder-only "
                    "coverage (coverageType must be 'I')."
                )
            return "I"
        return requested_covtype

    # NOTE: the legacy checkGroup() restriction against MXR_ELIG_XREF
    # (CLIENT/GROUP/CARRIER6/VALUE check types) is intentionally not ported yet --
    # its real column names/semantics were never available. Deferred until that
    # source is provided.

    async def _check_overlap(
        self,
        subscriber: str,
        clientcode: str,
        candidate_start: date,
        candidate_end: date | None,
        *,
        exclude_linenum: int | None = None,
    ) -> None:
        existing = await self._repo.get_by_subscriber(subscriber, clientcode)
        for row in existing:
            if exclude_linenum is not None and row.linenum == exclude_linenum:
                continue
            if _ranges_overlap(candidate_start, candidate_end, row.startdt, row.enddt):
                raise EligibilityDateOverlapException(
                    "Eligibility dates overlap with an existing record."
                )

    async def list_eligibility(self, subscribernum: str) -> list[SubscriberGroupInfo]:
        await self._require_subscriber(subscribernum)
        groups = await self._repo.get_by_subscriber(subscribernum, DEFAULT_CLIENTCODE)
        return [self._to_info(g) for g in groups]

    async def add_eligibility(
        self, subscribernum: str, request: EligibilityCreate
    ) -> SubscriberGroupInfo:
        await self._require_subscriber(subscribernum)

        covtype = await self._resolve_covtype(request.groupnum, request.covtype)
        await self._check_overlap(
            subscribernum, DEFAULT_CLIENTCODE, request.startdt, request.enddt
        )

        next_linenum = (
            await self._repo.get_max_linenum(subscribernum, DEFAULT_CLIENTCODE) + 1
        )
        group = SubscriberGroupListModel(
            subscriber=subscribernum,
            clientcode=DEFAULT_CLIENTCODE,
            linenum=next_linenum,
            groupnum=request.groupnum,
            priority=next_linenum,
            startdt=request.startdt,
            enddt=request.enddt,
            covtype=covtype,
            changedt=date.today(),
        )
        await self._repo.add(group)
        await self._session.commit()
        await self._session.refresh(group)
        return self._to_info(group)

    async def update_eligibility(
        self, subscribernum: str, linenum: int, request: EligibilityUpdate
    ) -> SubscriberGroupInfo:
        await self._require_subscriber(subscribernum)

        group = await self._repo.get_by_line(subscribernum, DEFAULT_CLIENTCODE, linenum)
        if group is None:
            raise SubscriberGroupNotFoundException(
                f"Group-eligibility line {linenum} not found for subscriber "
                f"'{subscribernum}'."
            )

        covtype = await self._resolve_covtype(request.groupnum, request.covtype)
        await self._check_overlap(
            subscribernum,
            DEFAULT_CLIENTCODE,
            request.startdt,
            request.enddt,
            exclude_linenum=linenum,
        )

        group.groupnum = request.groupnum
        group.startdt = request.startdt
        group.enddt = request.enddt
        group.covtype = covtype
        group.changedt = date.today()

        await self._session.commit()
        await self._session.refresh(group)
        return self._to_info(group)
