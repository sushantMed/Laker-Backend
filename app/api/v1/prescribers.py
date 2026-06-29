from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import bearer
from app.database.session import get_db
from app.schemas.common_schema import ApiResponse, PagedApiResponse
from app.schemas.prescriber_schema import PrescriberInfo, PrescriberSearchRequest
from app.services.prescriber_service import PrescriberService

router = APIRouter(prefix="/prescribers", tags=["Prescribers"])


@router.post("/search", response_model=PagedApiResponse[PrescriberInfo])
async def search_prescribers(
    request: PrescriberSearchRequest,
    session: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> PagedApiResponse[PrescriberInfo]:
    data = await PrescriberService(session).search_prescribers(request)
    return PagedApiResponse.ok(data=data, message="Prescribers retrieved successfully.")


@router.get("/{npi}", response_model=ApiResponse[PrescriberInfo])
async def get_prescriber(
    npi: str,
    session: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> ApiResponse[PrescriberInfo]:
    data = await PrescriberService(session).get_prescriber_by_npi(npi)
    return ApiResponse.ok(data=data, message="Prescriber retrieved successfully.")
