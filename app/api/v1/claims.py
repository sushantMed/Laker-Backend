"""
Claim controller (routes).

Thin layer: auth + dependency wiring only. All business logic and
exception raising lives in ClaimService. Exceptions raised there
(LakerBaseException subclasses) are mapped to HTTP status codes by a
global exception handler -- not here.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore

from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user_model import UserModel
from app.schemas.claim_schema import (
    ClaimDetail,
    ClaimsByEntityQuery,
    ClaimSearchRequest,
    ClaimSearchRequestByMemberPath,
    ClaimSummary,
)
from app.schemas.common_schema import ApiResponse, PagedApiResponse
from app.services.claim_service import ClaimService, _to_claim_detail, _to_claim_summary

router = APIRouter(tags=["Claims"])


CLAIM_RETRIEVAL_SUCCESS_MESSAGE = "Claims retrieved successfully."
RECENT_CLAIM_RETRIEVAL_SUCCESS_MESSAGE = "Recent claims retrieved successfully."
CLAIM_RETRIEVAL_DAYS = 90


@router.post("/claims/search")
async def search_claims(
    request: ClaimSearchRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    pageSize: Annotated[int, Query(ge=1, le=100, alias="pageSize")] = 10,
) -> PagedApiResponse[ClaimSummary]:
    data = await ClaimService(session).search_claims(request)
    return PagedApiResponse.ok(data=data, message=CLAIM_RETRIEVAL_SUCCESS_MESSAGE)


@router.get("/claims/{authNum}", status_code=status.HTTP_200_OK)
async def get_claim(
    authNum: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> ApiResponse[ClaimDetail]:
    detail = await ClaimService(session).get_claim_by_auth_num(authNum)
    return ApiResponse.ok(data=detail, message="Claim retrieved successfully.")


@router.post("/members/{memberId}/claims/search")
async def search_claims_for_member(
    memberId: str,
    request: ClaimSearchRequestByMemberPath,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    pageSize: Annotated[int, Query(ge=1, le=100, alias="pageSize")] = 10,
) -> PagedApiResponse[ClaimSummary]:
    data = await ClaimService(session).search_claims_for_member(memberId, request)
    return PagedApiResponse.ok(data=data, message=CLAIM_RETRIEVAL_SUCCESS_MESSAGE)


@router.get("/members/{memberId}/claims", status_code=status.HTTP_200_OK)
async def get_claims_for_member(
    memberId: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    pageSize: Annotated[int, Query(ge=1, le=100, alias="pageSize")] = 10,
) -> PagedApiResponse[ClaimSummary]:
    query = ClaimsByEntityQuery(page=page, pageSize=pageSize)
    data = await ClaimService(session).get_claims_for_member(
        memberId, query, transform=_to_claim_summary
    )
    return PagedApiResponse.ok(data=data, message=CLAIM_RETRIEVAL_SUCCESS_MESSAGE)


@router.get("/members/{memberId}/recent-claims", status_code=status.HTTP_200_OK)
async def get_recent_claims_for_member(
    memberId: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    pageSize: Annotated[int, Query(ge=1, le=100, alias="pageSize")] = 10,
) -> PagedApiResponse[ClaimDetail]:
    today = date.today()
    query = ClaimsByEntityQuery(
        page=page,
        pageSize=pageSize,
        startDate=(today - timedelta(days=CLAIM_RETRIEVAL_DAYS)).isoformat(),
        endDate=today.isoformat(),
    )
    data = await ClaimService(session).get_claims_for_member(
        memberId, query, transform=_to_claim_detail
    )
    return PagedApiResponse.ok(
        data=data, message=RECENT_CLAIM_RETRIEVAL_SUCCESS_MESSAGE
    )


@router.get("/pharmacies/{nabp}/claims", status_code=status.HTTP_200_OK)
async def get_claims_for_pharmacy(
    nabp: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    pageSize: Annotated[int, Query(ge=1, le=100, alias="pageSize")] = 10,
    startDate: Annotated[str | None, Query(alias="startDate")] = None,
    endDate: Annotated[str | None, Query(alias="endDate")] = None,
) -> PagedApiResponse[ClaimSummary]:
    query = ClaimsByEntityQuery(
        page=page, pageSize=pageSize, startDate=startDate, endDate=endDate
    )
    data = await ClaimService(session).get_claims_for_pharmacy(nabp, query)
    return PagedApiResponse.ok(data=data, message=CLAIM_RETRIEVAL_SUCCESS_MESSAGE)


@router.get("/prescribers/{npi}/claims", status_code=status.HTTP_200_OK)
async def get_claims_for_prescriber(
    npi: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    pageSize: Annotated[int, Query(ge=1, le=100, alias="pageSize")] = 10,
    startDate: Annotated[str | None, Query(alias="startDate")] = None,
    endDate: Annotated[str | None, Query(alias="endDate")] = None,
) -> PagedApiResponse[ClaimSummary]:
    query = ClaimsByEntityQuery(
        page=page, pageSize=pageSize, startDate=startDate, endDate=endDate
    )
    data = await ClaimService(session).get_claims_for_prescriber(npi, query)
    return PagedApiResponse.ok(data=data, message=CLAIM_RETRIEVAL_SUCCESS_MESSAGE)


@router.get("/drugs/{ndc}/claims", status_code=status.HTTP_200_OK)
async def get_claims_for_drug(
    ndc: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    pageSize: Annotated[int, Query(ge=1, le=100, alias="pageSize")] = 10,
    startDate: Annotated[str | None, Query(alias="startDate")] = None,
    endDate: Annotated[str | None, Query(alias="endDate")] = None,
) -> PagedApiResponse[ClaimSummary]:
    query = ClaimsByEntityQuery(
        page=page, pageSize=pageSize, startDate=startDate, endDate=endDate
    )
    data = await ClaimService(session).get_claims_for_drug(ndc, query)
    return PagedApiResponse.ok(data=data, message=CLAIM_RETRIEVAL_SUCCESS_MESSAGE)
