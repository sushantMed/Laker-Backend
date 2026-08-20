from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import (
    InvalidSearchCriteriaException,
    PharmacyNotFoundException,
)
from app.models.pharmacy_model import PharmacyModel
from app.schemas.pharmacy_schema import (
    PharmacyInfo,
    PharmacyLookupRequest,
    PharmacySearch,
    PharmacySearchRequest,
)
from app.services.pharmacy_service import (
    PharmacyService,
    _resolve_sort,
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
    )


@pytest.fixture
def service() -> PharmacyService:
    svc = PharmacyService(session=AsyncMock())
    svc._repo = AsyncMock()
    return svc


def test_to_pharmacy_info_maps_all_fields(service: PharmacyService):
    pharmacy = make_pharmacy(is_24_hour=True, fax=None)
    info = service._to_pharmacy_info(pharmacy)

    assert isinstance(info, PharmacyInfo)
    assert info.nabp == pharmacy.nabp
    assert info.npi == pharmacy.npi
    assert info.pharmacy_name == pharmacy.pharmacy_name
    assert info.address == "100 Main St"
    assert info.phone == pharmacy.phone
    assert info.fax is None
    assert info.is_24_hour is True


def test_resolve_sort_replaces_id_with_default():
    assert _resolve_sort("id") == "pharmacy_name"


def test_resolve_sort_keeps_other_columns():
    assert _resolve_sort("city") == "city"


async def test_get_pharmacy_by_nabp_fetches(service: PharmacyService):
    pharmacy = make_pharmacy()
    service._repo.get_by_nabp.return_value = [pharmacy]

    result = await service.get_pharmacy(PharmacyLookupRequest(nabp=pharmacy.nabp))

    assert result.data[0].nabp == pharmacy.nabp
    assert result.pagination.total == 1
    service._repo.get_by_nabp.assert_awaited_once_with(pharmacy.nabp)


async def test_get_pharmacy_by_npi_fetches(service: PharmacyService):
    pharmacy = make_pharmacy()
    service._repo.get_by_npi.return_value = [pharmacy]

    result = await service.get_pharmacy(PharmacyLookupRequest(npi=pharmacy.npi))

    assert result.data[0].npi == pharmacy.npi
    assert result.pagination.total == 1
    service._repo.get_by_npi.assert_awaited_once_with(pharmacy.npi)


async def test_get_pharmacy_applies_requested_pagination(service: PharmacyService):
    pharmacies = [make_pharmacy(nabp=f"123456{i}") for i in range(3)]
    service._repo.get_by_nabp.return_value = pharmacies

    result = await service.get_pharmacy(
        PharmacyLookupRequest(nabp="123456", page=2, pageSize=1)
    )

    assert [item.nabp for item in result.data] == ["1234561"]
    assert result.pagination.total == 3
    assert result.pagination.page == 2
    assert result.pagination.page_size == 1
    assert result.pagination.has_next is True
    assert result.pagination.has_prev is True


async def test_get_pharmacy_raises_when_missing(service: PharmacyService):
    service._repo.get_by_nabp.return_value = None

    with pytest.raises(PharmacyNotFoundException) as exc:
        await service.get_pharmacy(PharmacyLookupRequest(nabp="0000000"))

    assert exc.value.status_code == 404


def test_lookup_request_requires_identifier():
    from app.core.exceptions import MissingSearchCriteriaException

    with pytest.raises(MissingSearchCriteriaException):
        PharmacyLookupRequest()


def test_lookup_request_rejects_both_identifiers():
    from app.core.exceptions import InvalidSearchCriteriaException

    with pytest.raises(InvalidSearchCriteriaException):
        PharmacyLookupRequest(nabp="1234567", npi="1023456789")


@pytest.mark.parametrize("zip_code", ["6270", "62704-1234", "62704-123", "6270A"])
def test_lookup_request_rejects_invalid_us_zip_code(zip_code: str):
    with pytest.raises(InvalidSearchCriteriaException) as exc:
        PharmacyLookupRequest(zipCode=zip_code)

    assert exc.value.message == (
        "zipCode must be a valid five-digit U.S. ZIP code (for example, 62704)."
    )


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
