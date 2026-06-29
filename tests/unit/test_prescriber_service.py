from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import PrescriberNotFoundException
from app.models.prescriber_model import PrescriberModel
from app.schemas.prescriber_schema import (
    PrescriberInfo,
    PrescriberSearch,
    PrescriberSearchRequest,
)
from app.services import prescriber_service as prescriber_service_module
from app.services.prescriber_service import (
    PrescriberService,
    _compose_address,
    _resolve_sort,
    _to_prescriber_info,
)


def make_prescriber(
    npi: str = "1023456789",
    dea: str | None = "AB1234567",
    name: str = "Dr. Jane Smith",
    specialty: str | None = "Cardiology",
    address_line1: str = "200 Health Ave",
    city: str = "Chicago",
    state: str = "IL",
    zip: str = "60601",
    phone: str | None = "3125551234",
    fax: str | None = "3125555678",
) -> PrescriberModel:
    return PrescriberModel(
        npi=npi,
        dea=dea,
        name=name,
        specialty=specialty,
        address_line1=address_line1,
        city=city,
        state=state,
        zip=zip,
        phone=phone,
        fax=fax,
    )


@pytest.fixture
def service() -> PrescriberService:
    svc = PrescriberService(session=AsyncMock())
    svc._repo = AsyncMock()
    svc._cache = AsyncMock()
    return svc


def test_compose_address_formats_full_line():
    prescriber = make_prescriber()
    assert _compose_address(prescriber) == "200 Health Ave, Chicago, IL 60601"


def test_to_prescriber_info_maps_all_fields():
    prescriber = make_prescriber()
    info = _to_prescriber_info(prescriber)

    assert isinstance(info, PrescriberInfo)
    assert info.npi == prescriber.npi
    assert info.dea == prescriber.dea
    assert info.name == prescriber.name
    assert info.specialty == prescriber.specialty
    assert info.address == "200 Health Ave, Chicago, IL 60601"
    assert info.phone == prescriber.phone
    assert info.fax == prescriber.fax


def test_to_prescriber_info_handles_optional_nones():
    prescriber = make_prescriber(dea=None, specialty=None, phone=None, fax=None)
    info = _to_prescriber_info(prescriber)

    assert info.dea is None
    assert info.specialty is None
    assert info.phone is None
    assert info.fax is None


def test_resolve_sort_replaces_id_with_default():
    assert _resolve_sort("id") == "name"


def test_resolve_sort_keeps_other_columns():
    assert _resolve_sort("specialty") == "specialty"


async def test_get_prescriber_by_npi_returns_cached(service: PrescriberService):
    cached = _to_prescriber_info(make_prescriber())
    service._cache.get.return_value = cached

    result = await service.get_prescriber_by_npi("1023456789")

    assert result is cached
    service._cache.get.assert_awaited_once()
    service._repo.get_by_npi.assert_not_called()


async def test_get_prescriber_by_npi_fetches_and_caches_on_miss(
    service: PrescriberService,
):
    service._cache.get.return_value = None
    prescriber = make_prescriber()
    service._repo.get_by_npi.return_value = prescriber

    result = await service.get_prescriber_by_npi(prescriber.npi)

    assert result.npi == prescriber.npi
    service._repo.get_by_npi.assert_awaited_once_with(prescriber.npi)
    service._cache.set.assert_awaited_once()
    set_args = service._cache.set.await_args.args
    assert set_args[0] == prescriber.npi
    assert isinstance(set_args[1], PrescriberInfo)


async def test_get_prescriber_by_npi_raises_when_missing(service: PrescriberService):
    service._cache.get.return_value = None
    service._repo.get_by_npi.return_value = None

    with pytest.raises(PrescriberNotFoundException) as exc:
        await service.get_prescriber_by_npi("0000000000")

    assert exc.value.status_code == 404
    service._cache.set.assert_not_called()


async def test_search_prescribers_returns_paged_response(service: PrescriberService):
    prescribers = [make_prescriber(npi="1023456789"), make_prescriber(npi="1987654321")]
    service._repo.search.return_value = (prescribers, 2)
    request = PrescriberSearchRequest(
        searchRequest=PrescriberSearch(specialty="Cardiology")
    )

    result = await service.search_prescribers(request)

    assert len(result.data) == 2
    assert result.pagination.total == 2
    called = service._repo.search.await_args
    assert called.kwargs["sort_by"] == "name"


async def test_search_prescribers_raises_when_empty(service: PrescriberService):
    service._repo.search.return_value = ([], 0)
    request = PrescriberSearchRequest(searchRequest=PrescriberSearch(name="Nobody"))

    with pytest.raises(PrescriberNotFoundException):
        await service.search_prescribers(request)


def test_service_uses_prescriber_namespace(monkeypatch):
    captured = {}

    class FakeCache:
        def __init__(self, namespace: str) -> None:
            captured["namespace"] = namespace

    monkeypatch.setattr(prescriber_service_module, "CacheService", FakeCache)
    PrescriberService(session=AsyncMock())

    assert captured["namespace"] == "prescriber"
