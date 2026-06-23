from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.cache_service import CacheService
from app.core.exceptions import PrescriberNotFoundException
from app.models.prescriber_model import PrescriberModel
from app.repositories.prescriber_repository import PrescriberRepository
from app.schemas.prescriber_schema import PrescriberInfo, PrescriberSearchRequest
from app.utils.pagination import PagedResponse

_DEFAULT_SORT = "name"


def _compose_address(p: PrescriberModel) -> str:
    return f"{p.address_line1}, {p.city}, {p.state} {p.zip}"


def _to_prescriber_info(p: PrescriberModel) -> PrescriberInfo:
    return PrescriberInfo(
        npi=p.npi,
        dea=p.dea,
        name=p.name,
        specialty=p.specialty,
        address=_compose_address(p),
        phone=p.phone,
        fax=p.fax,
    )


def _resolve_sort(sort_by: str) -> str:
    return _DEFAULT_SORT if sort_by == "id" else sort_by


class PrescriberService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PrescriberRepository(session)
        self._cache = CacheService(namespace="prescriber")

    async def get_prescriber_by_npi(self, npi: str) -> PrescriberInfo:
        cached = await self._cache.get(npi, PrescriberInfo)
        if cached:
            return cached

        prescriber = await self._repo.get_by_npi(npi)
        if not prescriber:
            raise PrescriberNotFoundException(f"Prescriber '{npi}' not found.")

        info = _to_prescriber_info(prescriber)
        await self._cache.set(npi, info)
        return info

    async def search_prescribers(
        self, request: PrescriberSearchRequest
    ) -> PagedResponse[PrescriberInfo]:
        items, total = await self._repo.search(
            request.searchRequest,
            page=request.pagination.page,
            page_size=request.pagination.page_size,
            sort_by=_resolve_sort(request.sort.sort_by),
            sort_dir=request.sort.sort_dir,
        )
        if not items:
            raise PrescriberNotFoundException(
                "No prescribers found matching the search criteria."
            )
        return PagedResponse.of(
            data=[_to_prescriber_info(p) for p in items],
            page=request.pagination.page,
            page_size=request.pagination.page_size,
            total=total,
        )
