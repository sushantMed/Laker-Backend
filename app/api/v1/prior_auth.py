from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore

from app.core.permissions import RequireUser
from app.core.rbac import Perm
from app.database.session import get_db
from app.schemas.common_schema import PagedApiResponse
from app.schemas.prior_auth_schema import (
    # CreatePARequest,
    # PAByEntityQuery,
    # PADetail,
    PAMemberSearchResult,
    # PASearchRequest,
    PASearchRequestBySubscriber,
    # PASearchResult,
    # PatchPARequest,
    # UpdatePARequest,
)
from app.services.prior_auth_service import PriorAuthService

router = APIRouter(tags=["Prior Authorizations"])

PA_RETRIEVAL_SUCCESS_MESSAGE = "Prior authorizations retrieved successfully."
PA_DETAIL_SUCCESS_MESSAGE = "Prior authorization retrieved successfully."


# @router.post("/prior-auth/search", include_in_schema=False)
# async def search_prior_auths(
#     request: PASearchRequest,
#     session: Annotated[AsyncSession, Depends(get_db)],
#     current_user: RequireUser(Perm.MEMBERPRIORAUTH_VIEW),
# ) -> PagedApiResponse[PASearchResult]:
#     data = await PriorAuthService(session).search_prior_auths(request)
#     return PagedApiResponse.ok(data=data, message=PA_RETRIEVAL_SUCCESS_MESSAGE)


# @router.post(
#     "/prior-auth", status_code=status.HTTP_201_CREATED, include_in_schema=False
# )
# async def create_prior_auth(
#     request: CreatePARequest,
#     session: Annotated[AsyncSession, Depends(get_db)],
#     current_user: RequireUser(Perm.MEMBERPRIORAUTH_SAVE),
# ) -> ApiResponse[PADetail]:
#     detail = await PriorAuthService(session).create_prior_auth(
#         request, actor=current_user.email
#     )
#     return ApiResponse.ok(
#         data=detail, message="Prior authorization created successfully."
#     )


# @router.get(
#     "/prior-auth/{paId}", status_code=status.HTTP_200_OK, include_in_schema=False
# )
# async def get_prior_auth(
#     paId: str,
#     session: Annotated[AsyncSession, Depends(get_db)],
#     current_user: RequireUser(Perm.MEMBERPRIORAUTH_VIEW),
# ) -> ApiResponse[PADetail]:
#     detail = await PriorAuthService(session).get_prior_auth(paId)
#     return ApiResponse.ok(data=detail, message=PA_DETAIL_SUCCESS_MESSAGE)


# @router.put(
#     "/prior-auth/{paId}", status_code=status.HTTP_200_OK, include_in_schema=False
# )
# async def update_prior_auth(
#     paId: str,
#     request: UpdatePARequest,
#     session: Annotated[AsyncSession, Depends(get_db)],
#     current_user: RequireUser(Perm.MEMBERPRIORAUTH_SAVE),
# ) -> ApiResponse[PADetail]:
#     detail = await PriorAuthService(session).update_prior_auth(
#         paId, request, actor=current_user.email
#     )
#     return ApiResponse.ok(
#         data=detail, message="Prior authorization updated successfully."
#     )


# @router.patch(
#     "/prior-auth/{paId}", status_code=status.HTTP_200_OK, include_in_schema=False
# )
# async def patch_prior_auth(
#     paId: str,
#     request: PatchPARequest,
#     session: Annotated[AsyncSession, Depends(get_db)],
#     current_user: RequireUser(Perm.MEMBERPRIORAUTH_SAVE),
# ) -> ApiResponse[PADetail]:
#     detail = await PriorAuthService(session).patch_prior_auth(
#         paId, request, actor=current_user.email
#     )
#     return ApiResponse.ok(
#         data=detail, message="Prior authorization updated successfully."
#     )


# @router.get(
#     "/members/{memberId}/prior-auth",
#     status_code=status.HTTP_200_OK,
#     include_in_schema=False,
# )
# async def get_prior_auths_for_member(
#     memberId: str,
#     session: Annotated[AsyncSession, Depends(get_db)],
#     current_user: RequireUser(Perm.MEMBERPRIORAUTH_VIEW),
#     page: Annotated[int, Query(ge=1)] = 1,
#     pageSize: Annotated[int, Query(ge=1, le=100, alias="pageSize")] = 20,
#     status_filter: Annotated[PAStatus | None, Query(alias="status")] = None,
# ) -> PagedApiResponse[PASearchResult]:
#     query = PAByEntityQuery(page=page, pageSize=pageSize, status=status_filter)
#     data = await PriorAuthService(session).get_prior_auths_for_member(memberId, query)
#     return PagedApiResponse.ok(data=data, message=PA_RETRIEVAL_SUCCESS_MESSAGE)


# NOTE: the commented-out search_prior_auths above claims this same path. Only
# one of the two can be mounted -- FastAPI would silently route every request to
# whichever is registered first.
@router.post("/prior-auth/search")
async def search_prior_auths_for_subscriber(
    request: PASearchRequestBySubscriber,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: RequireUser(Perm.MEMBERPRIORAUTH_VIEW),
) -> PagedApiResponse[PAMemberSearchResult]:
    """Prior auths for one cardholder, keyed by subscriberNum + personCodes."""
    data = await PriorAuthService(session).search_prior_auths_for_subscriber(request)
    return PagedApiResponse.ok(data=data, message=PA_RETRIEVAL_SUCCESS_MESSAGE)


# @router.get(
#     "/drugs/{ndc}/prior-auth", status_code=status.HTTP_200_OK, include_in_schema=False
# )
# async def get_prior_auths_for_drug(
#     ndc: str,
#     session: Annotated[AsyncSession, Depends(get_db)],
#     current_user: RequireUser(Perm.MEMBERPRIORAUTH_VIEW),
#     page: Annotated[int, Query(ge=1)] = 1,
#     pageSize: Annotated[int, Query(ge=1, le=100, alias="pageSize")] = 20,
#     status_filter: Annotated[PAStatus | None, Query(alias="status")] = None,
# ) -> PagedApiResponse[PASearchResult]:
#     query = PAByEntityQuery(page=page, pageSize=pageSize, status=status_filter)
#     data = await PriorAuthService(session).get_prior_auths_for_drug(ndc, query)
#     return PagedApiResponse.ok(data=data, message=PA_RETRIEVAL_SUCCESS_MESSAGE)
