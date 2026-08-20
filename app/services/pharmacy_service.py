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
            address=p.address_line1,
            phone=p.phone,
            fax=p.fax,
            city=p.city,
            state=p.state,
            is24Hour=p.is_24_hour,
            zipCode=p.zip,
            longitude=p.longitude,
            latitude=p.latitude,
            distance_miles=getattr(p, "distance_miles", None),
        )

    async def get_pharmacy(
        self, request: PharmacyLookupRequest
    ) -> PagedResponse[PharmacyInfo]:
        if request.nabp:
            pharmacies = await self._repo.get_by_nabp(request.nabp)

        elif request.npi:
            pharmacies = await self._repo.get_by_npi(request.npi)
        else:
            pharmacies = await self._repo.get_by_zip_code(
                request.zip_code,
                radius=request.radius,
                is_24hr=request.is_24_hour,
            )

        if not pharmacies:
            raise PharmacyNotFoundException("Pharmacy not found.")

        total = len(pharmacies)
        offset = request.offset
        return PagedResponse.of(
            data=[
                self._to_pharmacy_info(pharmacy)
                for pharmacy in pharmacies[offset : offset + request.page_size]
            ],
            page=request.page,
            page_size=request.page_size,
            total=total,
        )

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
