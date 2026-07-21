from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import DrugNotFoundException
from app.models.drug_model import DrugModel
from app.schemas.drug_schema import (
    DrugInfo,
    DrugSearch,
    DrugSearchRequest,
    GpiLookupRequest,
)
from app.services import drug_service as drug_service_module
from app.services.drug_service import DrugService, _resolve_sort, _to_drug_info
from app.utils.enums import BrandGeneric, Maintenance


def make_drug(
    ndc: str = "00093721410",
    gpi: str = "39400010100310",
    drug_name: str = "Atorvastatin",
    brand_generic: BrandGeneric = BrandGeneric.GENERIC,
    maintenance: Maintenance = Maintenance.YES,
    desi: str | None = None,
    tier: int | None = 1,
    formulary_status: str | None = "PREFERRED",
    repackage_ind: bool = False,
) -> DrugModel:
    return DrugModel(
        ndc=ndc,
        gpi=gpi,
        drug_name=drug_name,
        brand_generic=brand_generic,
        maintenance=maintenance,
        desi=desi,
        tier=tier,
        formulary_status=formulary_status,
        repackage_ind=repackage_ind,
    )


@pytest.fixture
def service() -> DrugService:
    svc = DrugService(session=AsyncMock())
    svc._repo = AsyncMock()
    svc._cache = AsyncMock()
    return svc


def test_to_drug_info_maps_all_fields():
    drug = make_drug(desi="5", tier=3, formulary_status="NON_PREFERRED")
    info = _to_drug_info(drug)

    assert isinstance(info, DrugInfo)
    assert info.ndc == drug.ndc
    assert info.gpi == drug.gpi
    assert info.drug_name == drug.drug_name
    assert info.brand_generic == BrandGeneric.GENERIC
    assert info.maintenance == Maintenance.YES
    assert info.desi == "5"
    assert info.tier == 3
    assert info.formulary_status == "NON_PREFERRED"
    assert info.repackage_ind is False


def test_to_drug_info_handles_optional_nones():
    drug = make_drug(desi=None, tier=None, formulary_status=None)
    info = _to_drug_info(drug)

    assert info.desi is None
    assert info.tier is None
    assert info.formulary_status is None


def test_resolve_sort_replaces_id_with_default():
    assert _resolve_sort("id") == "drug_name"


def test_resolve_sort_keeps_other_columns():
    assert _resolve_sort("ndc") == "ndc"


async def test_get_drug_by_ndc_returns_cached(service: DrugService):
    cached = _to_drug_info(make_drug())
    service._cache.get.return_value = cached

    result = await service.get_drug_by_ndc("00093721410")

    assert result is cached
    service._cache.get.assert_awaited_once()
    service._repo.get_by_ndc.assert_not_called()


async def test_get_drug_by_ndc_fetches_and_caches_on_miss(service: DrugService):
    service._cache.get.return_value = None
    drug = make_drug()
    service._repo.get_by_ndc.return_value = drug

    result = await service.get_drug_by_ndc(drug.ndc)

    assert result.ndc == drug.ndc
    service._repo.get_by_ndc.assert_awaited_once_with(drug.ndc)
    service._cache.set.assert_awaited_once()
    set_args = service._cache.set.await_args.args
    assert set_args[0] == drug.ndc
    assert isinstance(set_args[1], DrugInfo)


async def test_get_drug_by_ndc_raises_when_missing(service: DrugService):
    service._cache.get.return_value = None
    service._repo.get_by_ndc.return_value = None

    with pytest.raises(DrugNotFoundException) as exc:
        await service.get_drug_by_ndc("99999999999")

    assert exc.value.status_code == 404
    service._cache.set.assert_not_called()


async def test_get_drugs_by_gpi_returns_paged_response(service: DrugService):
    drugs = [make_drug(ndc="00093721410"), make_drug(ndc="00093721420")]
    service._repo.get_by_gpi.return_value = (drugs, 2)
    request = GpiLookupRequest(page=1, page_size=20, sortBy="id", sortDir="ASC")

    result = await service.get_drugs_by_gpi("39400010100310", request)

    assert len(result.data) == 2
    assert result.pagination.total == 2
    assert result.pagination.page == 1
    called = service._repo.get_by_gpi.await_args
    assert called.args[0] == "39400010100310"
    assert called.kwargs["sort_by"] == "drug_name"
    assert called.kwargs["sort_dir"] == "ASC"


async def test_get_drugs_by_gpi_raises_when_empty(service: DrugService):
    service._repo.get_by_gpi.return_value = ([], 0)
    request = GpiLookupRequest()

    with pytest.raises(DrugNotFoundException):
        await service.get_drugs_by_gpi("00000000000000", request)


async def test_search_drugs_returns_paged_response(service: DrugService):
    drugs = [make_drug()]
    service._repo.search.return_value = (drugs, 1)
    request = DrugSearchRequest(searchRequest=DrugSearch(name="Atorvastatin"))

    result = await service.search_drugs(request)

    assert len(result.data) == 1
    assert result.data[0].drug_name == "Atorvastatin"
    assert result.pagination.total == 1
    service._repo.search.assert_awaited_once()


async def test_search_drugs_returns_empty_when_no_match(service: DrugService):
    service._repo.search.return_value = ([], 0)
    request = DrugSearchRequest(searchRequest=DrugSearch(gpi="39400010100310"))

    result = await service.search_drugs(request)

    assert result.data == []
    assert result.pagination.total == 0


def test_service_uses_drug_namespace(monkeypatch):
    captured = {}

    class FakeCache:
        def __init__(self, namespace: str) -> None:
            captured["namespace"] = namespace

    monkeypatch.setattr(drug_service_module, "CacheService", FakeCache)
    DrugService(session=AsyncMock())

    assert captured["namespace"] == "drug"
