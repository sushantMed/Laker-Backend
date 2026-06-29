from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.cache_service import CacheService
from app.core.exceptions import DrugNotFoundException
from app.models.drug_model import DrugModel
from app.repositories.drug_repository import DrugRepository
from app.schemas.drug_schema import DrugInfo, DrugSearchRequest, GpiLookupRequest
from app.utils.pagination import PagedResponse

_DEFAULT_SORT = "drug_name"


def _to_drug_info(d: DrugModel) -> DrugInfo:
    return DrugInfo(
        ndc=d.ndc,
        gpi=d.gpi,
        drugName=d.drug_name,
        brandGeneric=d.brand_generic,
        maintenance=d.maintenance,
        desi=d.desi,
        tier=d.tier,
        formularyStatus=d.formulary_status,
        repackageInd=d.repackage_ind,
    )


def _resolve_sort(sort_by: str) -> str:
    return _DEFAULT_SORT if sort_by == "id" else sort_by


class DrugService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = DrugRepository(session)
        self._cache = CacheService(namespace="drug")

    async def get_drug_by_ndc(self, ndc: str) -> DrugInfo:
        cached = await self._cache.get(ndc, DrugInfo)
        if cached:
            return cached

        drug = await self._repo.get_by_ndc(ndc)
        if not drug:
            raise DrugNotFoundException(f"Drug '{ndc}' not found.")

        info = _to_drug_info(drug)
        await self._cache.set(ndc, info)
        return info

    async def get_drugs_by_gpi(
        self, gpi: str, request: GpiLookupRequest
    ) -> PagedResponse[DrugInfo]:
        items, total = await self._repo.get_by_gpi(
            gpi,
            page=request.page,
            page_size=request.page_size,
            sort_by=_resolve_sort(request.sort_by),
            sort_dir=request.sort_dir,
        )
        if not items:
            raise DrugNotFoundException(f"No drugs found for GPI '{gpi}'.")
        return PagedResponse.of(
            data=[_to_drug_info(d) for d in items],
            page=request.page,
            page_size=request.page_size,
            total=total,
        )

    async def search_drugs(
        self, request: DrugSearchRequest
    ) -> PagedResponse[DrugInfo]:
        items, total = await self._repo.search(
            request.searchRequest,
            page=request.pagination.page,
            page_size=request.pagination.page_size,
            sort_by=_resolve_sort(request.sort.sort_by),
            sort_dir=request.sort.sort_dir,
        )
        if not items:
            raise DrugNotFoundException(
                "No drugs found matching the search criteria."
            )
        return PagedResponse.of(
            data=[_to_drug_info(d) for d in items],
            page=request.pagination.page,
            page_size=request.pagination.page_size,
            total=total,
        )
