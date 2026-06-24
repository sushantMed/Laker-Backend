from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import PharmacyNotFoundException
from app.models.pharmacy_model import PharmacyModel
from app.schemas.pharmacy_schema import (
    PharmacyInfo,
    PharmacySearch,
    PharmacySearchRequest,
)
from app.services import pharmacy_service as pharmacy_service_module
from app.services.pharmacy_service import (
    PharmacyService,
    _compose_address,
    _resolve_sort,
    _to_pharmacy_info,
)


def make_pharmacy(
    nabp: str = "1234567",
    npi: str = "1023456789",
    pharmacy_name: str = "Main Street Pharmacy",
    address_line1: str = "100 Main St",
    city: str = "Springfield",
    state: str = "IL",
    zip: str = "62704",
    phone: str = "2175551234",
    fax: str | None = "2175555678",
    is_24_hour: bool = False,
    in_network: bool = True,
) -> PharmacyModel:
    return PharmacyModel(
        nabp=nabp,
        npi=npi,
        pharmacy_name=pharmacy_name,
        address_line1=address_line1,
        city=city,
        state=state,
        zip=zip,
        phone=phone,
        fax=fax,
        is_24_hour=is_24_hour,
        in_network=in_network,
    )


@pytest.fixture
def service() -> PharmacyService:
    svc = PharmacyService(session=AsyncMock())
    svc._repo = AsyncMock()
    svc._cache = AsyncMock()
    return svc


def test_compose_address_formats_full_line():
    pharmacy = make_pharmacy()
    assert _compose_address(pharmacy) == "100 Main St, Springfield, IL 62704"


def test_to_pharmacy_info_maps_all_fields():
    pharmacy = make_pharmacy(is_24_hour=True, in_network=False, fax=None)
    info = _to_pharmacy_info(pharmacy)

    assert isinstance(info, PharmacyInfo)
    assert info.nabp == pharmacy.nabp
    assert info.npi == pharmacy.npi
    assert info.pharmacy_name == pharmacy.pharmacy_name
    assert info.address == "100 Main St, Springfield, IL 62704"
    assert info.phone == pharmacy.phone
    assert info.fax is None
    assert info.is_24_hour is True
    assert info.in_network is False


def test_resolve_sort_replaces_id_with_default():
    assert _resolve_sort("id") == "pharmacy_name"


def test_resolve_sort_keeps_other_columns():
    assert _resolve_sort("city") == "city"


async def test_get_pharmacy_by_nabp_returns_cached(service: PharmacyService):
    cached = _to_pharmacy_info(make_pharmacy())
    service._cache.get.return_value = cached

    result = await service.get_pharmacy_by_nabp("1234567")

    assert result is cached
    service._cache.get.assert_awaited_once()
    service._repo.get_by_nabp.assert_not_called()


async def test_get_pharmacy_by_nabp_fetches_and_caches_on_miss(
    service: PharmacyService,
):
    service._cache.get.return_value = None
    pharmacy = make_pharmacy()
    service._repo.get_by_nabp.return_value = pharmacy

    result = await service.get_pharmacy_by_nabp(pharmacy.nabp)

    assert result.nabp == pharmacy.nabp
    service._repo.get_by_nabp.assert_awaited_once_with(pharmacy.nabp)
    service._cache.set.assert_awaited_once()
    set_args = service._cache.set.await_args.args
    assert set_args[0] == pharmacy.nabp
    assert isinstance(set_args[1], PharmacyInfo)


async def test_get_pharmacy_by_nabp_raises_when_missing(service: PharmacyService):
    service._cache.get.return_value = None
    service._repo.get_by_nabp.return_value = None

    with pytest.raises(PharmacyNotFoundException) as exc:
        await service.get_pharmacy_by_nabp("0000000")

    assert exc.value.status_code == 404
    service._cache.set.assert_not_called()


async def test_search_pharmacies_returns_paged_response(service: PharmacyService):
    pharmacies = [make_pharmacy(nabp="1234567"), make_pharmacy(nabp="7654321")]
    service._repo.search.return_value = (pharmacies, 2)
    request = PharmacySearchRequest(searchRequest=PharmacySearch(city="Springfield"))

    result = await service.search_pharmacies(request)

    assert len(result.data) == 2
    assert result.pagination.total == 2
    called = service._repo.search.await_args
    assert called.kwargs["sort_by"] == "pharmacy_name"


async def test_search_pharmacies_raises_when_empty(service: PharmacyService):
    service._repo.search.return_value = ([], 0)
    request = PharmacySearchRequest(searchRequest=PharmacySearch(state="IL"))

    with pytest.raises(PharmacyNotFoundException):
        await service.search_pharmacies(request)


def test_service_uses_pharmacy_namespace(monkeypatch):
    captured = {}

    class FakeCache:
        def __init__(self, namespace: str) -> None:
            captured["namespace"] = namespace

    monkeypatch.setattr(pharmacy_service_module, "CacheService", FakeCache)
    PharmacyService(session=AsyncMock())

    assert captured["namespace"] == "pharmacy"
