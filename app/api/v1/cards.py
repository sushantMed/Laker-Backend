from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore

from app.core.permissions import RequireUser
from app.core.rbac import Perm
from app.database.session import get_db
from app.schemas.card_schema import (
    CardPrintHistoryQuery,
    CardPrintHistoryRow,
    CardPrintHistorySearchRequest,
)
from app.schemas.common_schema import ApiResponse, PagedApiResponse
from app.services.card_service import CardService

router = APIRouter(tags=["Card Print"])

CARD_HISTORY_SUCCESS_MESSAGE = "Card print history retrieved successfully."


@router.get("/members/{memberId}/card-print-history", status_code=status.HTTP_200_OK)
async def get_card_print_history(
    memberId: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: RequireUser(Perm.MEMBER_VIEW),
    query: Annotated[CardPrintHistoryQuery, Depends()],
) -> PagedApiResponse[CardPrintHistoryRow]:
    data = await CardService(session).get_print_history(memberId, query)
    return PagedApiResponse.ok(data=data, message=CARD_HISTORY_SUCCESS_MESSAGE)


@router.post("/members/{memberId}/card-print-history/search")
async def search_card_print_history(
    memberId: str,
    request: CardPrintHistorySearchRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: RequireUser(Perm.MEMBER_VIEW),
) -> PagedApiResponse[CardPrintHistoryRow]:
    data = await CardService(session).search_print_history(memberId, request)
    return PagedApiResponse.ok(data=data, message=CARD_HISTORY_SUCCESS_MESSAGE)


@router.post(
    "/members/{memberId}/card-print-history/{cardQueueKey}/cancel",
    status_code=status.HTTP_200_OK,
)
async def cancel_card_print_request(
    memberId: str,
    cardQueueKey: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: RequireUser(Perm.MEMCARDCANCEL_SAVE),
) -> ApiResponse[CardPrintHistoryRow]:
    row = await CardService(session).cancel_card_request(
        memberId, cardQueueKey, actor=current_user.email
    )
    return ApiResponse.ok(
        data=row, message="Card print request cancelled successfully."
    )
