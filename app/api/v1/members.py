from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import bearer
from app.database.session import get_db  # adjust to his db path
from app.schemas.common_schema import ApiResponse, PagedApiResponse
from app.schemas.member_schema import (
    AddFamilyMemberRequest,
    EligibilityResponse,
    FamilyMembersRequest,
    MemberDetail,
    MemberSearchRequest,
    MemberSummary,
)
from app.services.member_service import MemberService

router = APIRouter(prefix="/members", tags=["Members"])


@router.get("/{member_id}", response_model=ApiResponse[MemberDetail])
async def get_member(
    member_id: str,
    session: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> ApiResponse[MemberDetail]:
    data = await MemberService(session).get_member_by_id(member_id)
    return ApiResponse.ok(data=data, message="Member retrieved successfully.")


@router.post("/search", response_model=PagedApiResponse[MemberSummary])
async def search_members(
    request: MemberSearchRequest,
    session: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> PagedApiResponse[MemberSummary]:
    data = await MemberService(session).search_members(request)
    return PagedApiResponse.ok(data=data, message="Members retrieved successfully.")


@router.get("/{member_id}/eligibility", response_model=ApiResponse[EligibilityResponse])
async def get_eligibility(
    member_id: str,
    session: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> ApiResponse[EligibilityResponse]:
    data = await MemberService(session).get_eligibility(member_id)
    return ApiResponse.ok(data=data, message="Eligibility retrieved successfully.")


@router.get("/{member_id}/family", response_model=PagedApiResponse[MemberSummary])
async def get_family(
    member_id: str,
    request: FamilyMembersRequest = Depends(),
    session: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> PagedApiResponse[MemberSummary]:
    data = await MemberService(session).get_family(member_id, request)
    return PagedApiResponse.ok(
        data=data, message="Family members retrieved successfully."
    )


@router.post(
    "/{member_id}/family",
    response_model=ApiResponse[MemberDetail],
    status_code=status.HTTP_201_CREATED,
)
async def add_family_member(
    member_id: str,
    request: AddFamilyMemberRequest,
    session: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> ApiResponse[MemberDetail]:
    data = await MemberService(session).add_family_member(member_id, request)
    return ApiResponse.ok(data=data, message="Family member added successfully.")
