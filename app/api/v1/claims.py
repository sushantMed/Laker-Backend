"""
Claim controller (routes).

Thin layer: auth + dependency wiring only. All business logic and
exception raising lives in ClaimService. Exceptions raised there
(LakerBaseException subclasses) are mapped to HTTP status codes by a
global exception handler -- not here.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import bearer
from app.database.session import get_db
from app.schemas.claim_schema import (
    ClaimDetail,
    ClaimSearchRequest,
    ClaimsByEntityQuery,
    ClaimSummary,
)
from app.schemas.common_schema import PagedApiResponse
from app.services.claim_service import ClaimService
from app.utils.pagination import PaginationRequest
from fastapi import status

router = APIRouter(prefix="/api/v1", tags=["Claims"])





@router.post("/claims/search", status_code=status.HTTP_200_OK)
async def search_claims(
    request: ClaimSearchRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
) -> PagedApiResponse[ClaimSummary]:
    data = await ClaimService(session).search_claims(request)
    return PagedApiResponse.ok(data=data, message="Claims retrieved successfully.")




@router.get("/claims/{authNum}")
async def get_claim(
    authNum: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
) -> ClaimDetail:
    return await ClaimService(session).get_claim_by_auth_num(authNum)




@router.post("/members/{memberId}/claims/search")
async def search_claims_for_member(
    memberId: str,
    request: ClaimSearchRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
) -> PagedApiResponse[ClaimSummary]:
    data = await ClaimService(session).search_claims_for_member(memberId, request)
    return PagedApiResponse.ok(data=data, message="Claims retrieved successfully.")




@router.get("/members/{memberId}/claims")
async def get_claims_for_member(
    memberId: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=100, alias="pageSize"),
) -> PagedApiResponse[ClaimSummary]:
    pagination = PaginationRequest(page=page, page_size=pageSize)
    data = await ClaimService(session).get_claims_for_member(memberId, pagination)
    return PagedApiResponse.ok(data=data, message="Claims retrieved successfully.")




@router.get("/pharmacies/{nabp}/claims")
async def get_claims_for_pharmacy(
    nabp: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=100, alias="pageSize"),
    startDate: str | None = Query(None, alias="startDate"),
    endDate: str | None = Query(None, alias="endDate"),
) -> PagedApiResponse[ClaimSummary]:
    query = ClaimsByEntityQuery(
        page=page, pageSize=pageSize, startDate=startDate, endDate=endDate
    )
    data = await ClaimService(session).get_claims_for_pharmacy(nabp, query)
    return PagedApiResponse.ok(data=data, message="Claims retrieved successfully.")




@router.get("/prescribers/{npi}/claims")
async def get_claims_for_prescriber(
    npi: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=100, alias="pageSize"),
    startDate: str | None = Query(None, alias="startDate"),
    endDate: str | None = Query(None, alias="endDate"),
) -> PagedApiResponse[ClaimSummary]:
    query = ClaimsByEntityQuery(
        page=page, pageSize=pageSize, startDate=startDate, endDate=endDate
    )
    data = await ClaimService(session).get_claims_for_prescriber(npi, query)
    return PagedApiResponse.ok(data=data, message="Claims retrieved successfully.")




@router.get("/drugs/{ndc}/claims")
async def get_claims_for_drug(
    ndc: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=100, alias="pageSize"),
    startDate: str | None = Query(None, alias="startDate"),
    endDate: str | None = Query(None, alias="endDate"),
) -> PagedApiResponse[ClaimSummary]:
    query = ClaimsByEntityQuery(
        page=page, pageSize=pageSize, startDate=startDate, endDate=endDate
    )
    data = await ClaimService(session).get_claims_for_drug(ndc, query)
    return PagedApiResponse.ok(data=data, message="Claims retrieved successfully.")