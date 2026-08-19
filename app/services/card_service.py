from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal, InvalidOperation

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    CardRequestNotCancellableException,
    CardRequestNotFoundException,
    MemberNotFoundException,
)
from app.models.card_queue_model import CardQueueModel
from app.models.member_model import MemberModel
from app.repositories.audit_repository import AuditRepository, FieldChange
from app.repositories.card_repository import (
    CANCELLED_REPORT_STATUS,
    CardRepository,
    is_cancelled,
    is_printed,
)
from app.repositories.member_repository import MemberRepository
from app.schemas.card_schema import (
    CardPrintHistoryQuery,
    CardPrintHistoryRow,
    CardPrintHistorySearchRequest,
)
from app.utils.pagination import PagedResponse

# Identifies the card-cancel action in the legacy UPDTRAN change log. TRANID 2
# is the "update" transaction; SCREENID is the Mem Cancel Card Request screen.
_CARD_CANCEL_TRAN_ID = 2
_CARD_CANCEL_SCREEN_ID = 0
_CARDQ_TABLE = "CARDQ"
_REPORT_STATUS_FIELD = "REPORTSTATUS"


def _format_key(key: Decimal | None) -> str:
    if key is None:
        return ""
    return str(int(key))


def _parse_key(key: str) -> Decimal | None:
    try:
        return Decimal(key.strip())
    except (InvalidOperation, AttributeError, ValueError):
        return None


def _to_int(value: Decimal | None) -> int | None:
    return int(value) if value is not None else None


def _to_row(card: CardQueueModel) -> CardPrintHistoryRow:
    return CardPrintHistoryRow(
        card_queue_key=_format_key(card.key),
        change_date=card.timestamp,
        print_date=card.printdate,
        batch_num=_to_int(card.batchnum),
        card_cancelled=is_cancelled(card),
        report_status=card.reportstatus,
    )


class CardService:
    """Card print history and card print request cancellation."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = CardRepository(session)
        self._member_repo = MemberRepository(session)
        self._audit_repo = AuditRepository(session)
        self._session = session

    async def get_print_history(
        self, member_id: str, query: CardPrintHistoryQuery
    ) -> PagedResponse[CardPrintHistoryRow]:
        member = await self._require_member(member_id)
        items, total = await self._repo.search_print_history(
            subscriber=member.insured_id or "",
            person_code=member.person_code,
            page=query.page,
            page_size=query.page_size,
            sort_by="changeDate",
            sort_dir="desc",
        )
        return _to_page(items, total, query.page, query.page_size)

    async def search_print_history(
        self, member_id: str, request: CardPrintHistorySearchRequest
    ) -> PagedResponse[CardPrintHistoryRow]:
        member = await self._require_member(member_id)
        criteria = request.searchRequest

        items, total = await self._repo.search_print_history(
            subscriber=member.insured_id or "",
            person_code=member.person_code,
            change_date_from=criteria.change_date_from,
            change_date_to=criteria.change_date_to,
            batch_num=criteria.batch_num,
            cancelled=criteria.card_cancelled,
            page=request.pagination.page,
            page_size=request.pagination.page_size,
            sort_by=request.sort.sort_by,
            sort_dir=request.sort.sort_dir,
        )
        return _to_page(
            items, total, request.pagination.page, request.pagination.page_size
        )

    async def cancel_card_request(
        self,
        member_id: str,
        card_queue_key: str,
        actor: str | None = None,
    ) -> CardPrintHistoryRow:
        """Cancel a still-queued card print request and log the change.

        Rows the nightly print job has already picked up (they carry a print
        date or batch number) are history and cannot be cancelled.
        """
        member = await self._require_member(member_id)
        card = await self._require_card(member, card_queue_key)

        if is_cancelled(card):
            raise CardRequestNotCancellableException(
                f"Card print request '{card_queue_key}' is already cancelled."
            )
        if is_printed(card):
            raise CardRequestNotCancellableException(
                f"Card print request '{card_queue_key}' has already been printed "
                "and cannot be cancelled."
            )

        previous_status = card.reportstatus
        card.reportstatus = CANCELLED_REPORT_STATUS

        await self._audit_repo.record(
            client_code=member.plan.group_number if member.plan else None,
            tran_id=_CARD_CANCEL_TRAN_ID,
            screen_id=_CARD_CANCEL_SCREEN_ID,
            screen_key=f"{member.insured_id or ''}{member.person_code or ''}",
            user_id=actor,
            changes=[
                FieldChange(
                    detail_key=_format_key(card.key),
                    upd_table=_CARDQ_TABLE,
                    field_name=_REPORT_STATUS_FIELD,
                    old_value=previous_status,
                    new_value=CANCELLED_REPORT_STATUS,
                )
            ],
        )

        await self._session.commit()
        await self._session.refresh(card)
        return _to_row(card)

    async def _require_member(self, member_id: str) -> MemberModel:
        member = await self._member_repo.get_by_member_id(member_id)
        if not member:
            raise MemberNotFoundException(f"Member '{member_id}' not found.")
        return member

    async def _require_card(
        self, member: MemberModel, card_queue_key: str
    ) -> CardQueueModel:
        key = _parse_key(card_queue_key)
        card = await self._repo.get_by_key(key) if key is not None else None
        # A row belonging to someone else is reported as missing rather than
        # forbidden -- the caller has no business knowing it exists.
        belongs_to_member = card is not None and (
            card.subscriber == member.insured_id
            and card.personcode == member.person_code
        )
        if not belongs_to_member:
            raise CardRequestNotFoundException(
                f"Card print request '{card_queue_key}' not found for member "
                f"'{member.member_id}'."
            )
        return card


def _to_page(
    items: Sequence[CardQueueModel], total: int, page: int, page_size: int
) -> PagedResponse[CardPrintHistoryRow]:
    return PagedResponse.of(
        data=[_to_row(card) for card in items],
        page=page,
        page_size=page_size,
        total=total,
    )
