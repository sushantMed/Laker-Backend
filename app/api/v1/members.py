from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user_model import UserModel
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


@router.get("/{member_id}", status_code=status.HTTP_200_OK)
async def get_member(
    member_id: str,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[MemberDetail]:
    detail = await MemberService(session).get_member_by_id(member_id)
    return ApiResponse.ok(data=detail, message="Member retrieved successfully.")


@router.post("/search")
async def search_members(
    request: MemberSearchRequest,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PagedApiResponse[MemberSummary]:
    data = await MemberService(session).search_members(request)
    return PagedApiResponse.ok(data=data, message="Members retrieved successfully.")


@router.get("/{member_id}/eligibility")
async def get_eligibility(
    member_id: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> ApiResponse[EligibilityResponse]:
    detail = await MemberService(session).get_eligibility(member_id)
    return ApiResponse.ok(data=detail, message="Eligibility retrieved successfully.")


@router.get("/{member_id}/family")
async def get_family(
    member_id: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
    request: Annotated[FamilyMembersRequest, Depends()],
) -> PagedApiResponse[MemberSummary]:
    data = await MemberService(session).get_family(member_id, request)
    return PagedApiResponse.ok(
        data=data, message="Family members retrieved successfully."
    )


@router.post(
    "/{member_id}/family",
    status_code=status.HTTP_201_CREATED,
)
async def add_family_member(
    member_id: str,
    request: AddFamilyMemberRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> ApiResponse[MemberDetail]:
    detail = await MemberService(session).add_family_member(member_id, request)
    return ApiResponse.ok(data=detail, message="Member added successfully")
