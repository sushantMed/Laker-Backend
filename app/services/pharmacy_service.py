from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.cache_service import CacheService
from app.core.exceptions import PharmacyNotFoundException
from app.models.pharmacy_model import PharmacyModel
from app.repositories.pharmacy_repository import PharmacyRepository
from app.schemas.pharmacy_schema import PharmacyInfo, PharmacySearchRequest
from app.utils.pagination import PagedResponse

_DEFAULT_SORT = "pharmacy_name"


def _compose_address(p: PharmacyModel) -> str:
    return f"{p.address_line1}, {p.city}, {p.state} {p.zip}"


def _to_pharmacy_info(p: PharmacyModel) -> PharmacyInfo:
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


def _resolve_sort(sort_by: str) -> str:
    return _DEFAULT_SORT if sort_by == "id" else sort_by


class PharmacyService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PharmacyRepository(session)
        self._cache = CacheService(namespace="pharmacy")

    async def get_pharmacy_by_nabp(self, nabp: str) -> PharmacyInfo:
        cached = await self._cache.get(nabp, PharmacyInfo)
        if cached:
            return cached

        pharmacy = await self._repo.get_by_nabp(nabp)
        if not pharmacy:
            raise PharmacyNotFoundException(f"Pharmacy '{nabp}' not found.")

        info = _to_pharmacy_info(pharmacy)
        await self._cache.set(nabp, info)
        return info

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
            data=[_to_pharmacy_info(p) for p in items],
            page=request.pagination.page,
            page_size=request.pagination.page_size,
            total=total,
        )
