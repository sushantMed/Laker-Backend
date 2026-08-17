from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import bearer
from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user_model import UserModel
from app.schemas.common_schema import PagedApiResponse
from app.schemas.pharmacy_schema import (
    PharmacyInfo,
    PharmacyLookupRequest,
    PharmacySearchRequest,
)
from app.services.pharmacy_service import PharmacyService

router = APIRouter(prefix="/pharmacies", tags=["Pharmacies"])


@router.post("/search", response_model=PagedApiResponse[PharmacyInfo])
async def search_pharmacies(
    request: PharmacySearchRequest,
    session: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> PagedApiResponse[PharmacyInfo]:
    data = await PharmacyService(session).search_pharmacies(request)
    return PagedApiResponse.ok(data=data, message="Pharmacies retrieved successfully.")


@router.get("", response_model=PagedApiResponse[PharmacyInfo])
async def get_pharmacy(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    request: PharmacyLookupRequest = Depends(),
    session: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> PagedApiResponse[PharmacyInfo]:
    data = await PharmacyService(session).get_pharmacy(request)
    return PagedApiResponse.ok(data=data, message="Pharmacy retrieved successfully.")
