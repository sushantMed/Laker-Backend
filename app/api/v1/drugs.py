from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user_model import UserModel
from app.schemas.common_schema import ApiResponse, PagedApiResponse
from app.schemas.drug_schema import (
    DrugInfo,
    DrugSearchRequest,
    GpiLookupRequest,
)
from app.services.drug_service import DrugService

router = APIRouter(prefix="/drugs", tags=["Drugs"])


@router.post("/search", response_model=PagedApiResponse[DrugInfo])
async def search_drugs(
    request: DrugSearchRequest,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
) -> PagedApiResponse[DrugInfo]:
    data = await DrugService(session).search_drugs(request)
    return PagedApiResponse.ok(data=data, message="Drugs retrieved successfully.")


@router.get("/gpi/{gpi}", response_model=PagedApiResponse[DrugInfo])
async def get_drugs_by_gpi(
    gpi: str,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    request: GpiLookupRequest = Depends(),
    session: AsyncSession = Depends(get_db),
) -> PagedApiResponse[DrugInfo]:
    data = await DrugService(session).get_drugs_by_gpi(gpi, request)
    return PagedApiResponse.ok(data=data, message="Drugs retrieved successfully.")


@router.get("/{ndc}", response_model=ApiResponse[DrugInfo])
async def get_drug(
    ndc: str,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[DrugInfo]:
    data = await DrugService(session).get_drug_by_ndc(ndc)
    return ApiResponse.ok(data=data, message="Drug retrieved successfully.")
