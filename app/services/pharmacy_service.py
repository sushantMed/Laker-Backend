from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PharmacyNotFoundException
from app.models.pharmacy_model import PharmacyModel
from app.repositories.pharmacy_repository import PharmacyRepository
from app.schemas.pharmacy_schema import (
    PharmacyInfo,
    PharmacyLookupRequest,
    PharmacySearchRequest,
)
from app.utils.pagination import PagedResponse

_DEFAULT_SORT = "pharmacy_name"


def _compose_address(p: PharmacyModel) -> str:
    return f"{p.address_line1}, {p.city}, {p.state} {p.zip}"


def _resolve_sort(sort_by: str) -> str:
    return _DEFAULT_SORT if sort_by == "id" else sort_by


class PharmacyService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PharmacyRepository(session)

    def _to_pharmacy_info(self, p: PharmacyModel) -> PharmacyInfo:
        return PharmacyInfo(
            nabp=p.nabp,
            npi=p.npi,
            pharmacyName=p.pharmacy_name,
            address=_compose_address(p),
            phone=p.phone,
            fax=p.fax,
            is24Hour=p.is_24_hour,
            inNetwork=p.in_network,
        )

    async def get_pharmacy(self, request: PharmacyLookupRequest) -> PharmacyInfo:
        pharmacy = (
            await self._repo.get_by_nabp(request.nabp)
            if request.nabp
            else await self._repo.get_by_npi(request.npi)
        )

        if not pharmacy:
            raise PharmacyNotFoundException("Pharmacy not found.")

        data = self._to_pharmacy_info(pharmacy)
        return data

    async def search_pharmacies(
        self, request: PharmacySearchRequest
    ) -> PagedResponse[PharmacyInfo]:
        items, total = await self._repo.search(
            request.searchRequest,
            page=request.pagination.page,
            page_size=request.pagination.page_size,
            sort_by=_resolve_sort(request.sort.sort_by),
            sort_dir=request.sort.sort_dir,
        )
        if not items:
            raise PharmacyNotFoundException(
                "No pharmacies found matching the search criteria."
            )
        return PagedResponse.of(
            data=[self._to_pharmacy_info(p) for p in items],
            page=request.pagination.page,
            page_size=request.pagination.page_size,
            total=total,
        )
