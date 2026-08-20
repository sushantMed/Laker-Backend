from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import RequireUser
from app.core.rbac import Perm
from app.database.session import get_db
from app.schemas.common_schema import ApiResponse
from app.schemas.subs_subgroups_schema import SubsSubgroupInfo
from app.schemas.subscob_schema import SubscobInfo
from app.schemas.subscriber_group_list_schema import (
    EligibilityCreate,
    EligibilityUpdate,
    SubscriberGroupInfo,
)
from app.services.subs_subgroups_service import SubsSubgroupsService
from app.services.subscob_service import SubscobService
from app.services.subscriber_group_list_service import SubscriberGroupListService

router = APIRouter(prefix="/members", tags=["Cardholder Eligibility"])

ELIGIBILITY_LIST_SUCCESS_MESSAGE = "Group-eligibility records retrieved successfully."
COB_LIST_SUCCESS_MESSAGE = "COB records retrieved successfully."
SUBGROUP_LIST_SUCCESS_MESSAGE = "Sub-group records retrieved successfully."


@router.get(
    "/group-eligibility",
    status_code=status.HTTP_200_OK,
)
async def list_eligibility(
    subscribernum: Annotated[str, Query()],
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: RequireUser(Perm.CARDHOLDERELIGIBILTY_VIEW),
) -> ApiResponse[list[SubscriberGroupInfo]]:
    data = await SubscriberGroupListService(session).list_eligibility(subscribernum)
    return ApiResponse.ok(data=data, message=ELIGIBILITY_LIST_SUCCESS_MESSAGE)


@router.post(
    "/group-eligibility",
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def add_eligibility(
    subscribernum: Annotated[str, Query()],
    request: EligibilityCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: RequireUser(Perm.CARDHOLDERELIGIBILTY_SAVE),
) -> ApiResponse[SubscriberGroupInfo]:
    data = await SubscriberGroupListService(session).add_eligibility(
        subscribernum, request
    )
    return ApiResponse.ok(
        data=data, message="Group-eligibility row added successfully."
    )


@router.put(
    "/group-eligibility/{linenum}",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def update_eligibility(
    linenum: int,
    subscribernum: Annotated[str, Query()],
    request: EligibilityUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: RequireUser(Perm.CARDHOLDERELIGIBILTY_SAVE),
) -> ApiResponse[SubscriberGroupInfo]:
    data = await SubscriberGroupListService(session).update_eligibility(
        subscribernum, linenum, request
    )
    return ApiResponse.ok(
        data=data, message="Group-eligibility row updated successfully."
    )


@router.get(
    "/cob",
    status_code=status.HTTP_200_OK,
)
async def list_cob(
    subscribernum: Annotated[str, Query()],
    personcode: Annotated[str, Query()],
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: RequireUser(Perm.CARDHOLDERELIGIBILTY_VIEW),
) -> ApiResponse[list[SubscobInfo]]:
    data = await SubscobService(session).list_other_coverage(subscribernum, personcode)
    return ApiResponse.ok(data=data, message=COB_LIST_SUCCESS_MESSAGE)


@router.get(
    "/subgroups",
    status_code=status.HTTP_200_OK,
)
async def list_subgroups(
    subscribernum: Annotated[str, Query()],
    personcode: Annotated[str, Query()],
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: RequireUser(Perm.CARDHOLDERELIGIBILTY_VIEW),
) -> ApiResponse[list[SubsSubgroupInfo]]:
    data = await SubsSubgroupsService(session).list_subgroups(subscribernum, personcode)
    return ApiResponse.ok(data=data, message=SUBGROUP_LIST_SUCCESS_MESSAGE)
