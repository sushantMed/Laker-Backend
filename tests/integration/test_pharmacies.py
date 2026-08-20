from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.pharmacy_model import PharmacyModel
from tests.integration.conftest import AUTH


@pytest.mark.asyncio
async def test_get_pharmacy_by_nabp_success(client, seeded_lookups):
    resp = await client.get(
        "/api/v1/pharmacies", params={"nabp": "1234567"}, headers=AUTH
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["pagination"]["total"] == 1
    assert body["data"][0]["nabp"] == "1234567"
    assert body["data"][0]["address"] == "100 Main St"
    assert body["data"][0]["is24Hour"] is True


@pytest.mark.asyncio
async def test_get_pharmacy_by_npi_success(client, seeded_lookups):
    resp = await client.get(
        "/api/v1/pharmacies", params={"npi": "1023456789"}, headers=AUTH
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["pagination"]["total"] == 1
    assert body["data"][0]["npi"] == "1023456789"


@pytest.mark.asyncio
async def test_get_pharmacy_by_nabp_not_found(client, seeded_lookups):
    resp = await client.get(
        "/api/v1/pharmacies", params={"nabp": "0000000"}, headers=AUTH
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_pharmacy_missing_identifier(client, seeded_lookups):
    resp = await client.get("/api/v1/pharmacies", headers=AUTH)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_pharmacy_both_identifiers_provided(client, seeded_lookups):
    resp = await client.get(
        "/api/v1/pharmacies",
        params={"nabp": "1234567", "npi": "1023456789"},
        headers=AUTH,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_pharmacy_requires_auth(raw_client, seeded_lookups):
    resp = await raw_client.get("/api/v1/pharmacies", params={"nabp": "1234567"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_search_pharmacies_by_city(client, seeded_lookups):
    resp = await client.post(
        "/api/v1/pharmacies/search",
        json={"searchRequest": {"city": "Chicago"}},
        headers=AUTH,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["pagination"]["total"] == 1
    assert body["data"][0]["pharmacyName"] == "Downtown Drugs"


@pytest.mark.asyncio
async def test_search_pharmacies_by_name_nabp_npi(client, seeded_lookups):
    resp = await client.post(
        "/api/v1/pharmacies/search",
        json={
            "searchRequest": {
                "name": "Main",
                "nabp": "1234567",
                "npi": "1023456789",
            }
        },
        headers=AUTH,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["pagination"]["total"] == 1
    assert body["data"][0]["nabp"] == "1234567"


@pytest.mark.asyncio
async def test_search_pharmacies_by_state_zip_and_network(client, seeded_lookups):
    resp = await client.post(
        "/api/v1/pharmacies/search",
        json={
            "searchRequest": {
                "state": "IL",
                "zipCode": "62704",
                "is24Hour": True,
                "inNetwork": True,
            }
        },
        headers=AUTH,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["pagination"]["total"] == 1
    assert body["data"][0]["pharmacyName"] == "Main Street Pharmacy"


@pytest.mark.asyncio
async def test_search_pharmacies_by_state(client, seeded_lookups):
    resp = await client.post(
        "/api/v1/pharmacies/search",
        json={"searchRequest": {"state": "IL"}},
        headers=AUTH,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["pagination"]["total"] == 2
    assert {pharmacy["pharmacyName"] for pharmacy in body["data"]} == {
        "Main Street Pharmacy",
        "Downtown Drugs",
    }


@pytest.mark.asyncio
async def test_get_pharmacies_by_zip_within_radius(client, db_session, seeded_lookups):
    pharmacies = {
        pharmacy.nabp: pharmacy
        for pharmacy in (
            await db_session.scalars(
                select(PharmacyModel).where(
                    PharmacyModel.nabp.in_(["1234567", "7654321"])
                )
            )
        )
    }
    pharmacies["1234567"].latitude = 39.7817
    pharmacies["1234567"].longitude = -89.6501
    pharmacies["7654321"].latitude = 41.8781
    pharmacies["7654321"].longitude = -87.6298
    await db_session.flush()

    resp = await client.get(
        "/api/v1/pharmacies",
        params={"zipCode": "62704", "radius": 5},
        headers=AUTH,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["pagination"]["total"] == 1
    assert [pharmacy["nabp"] for pharmacy in body["data"]] == ["1234567"]


@pytest.mark.asyncio
async def test_get_pharmacies_by_zip_with_zero_radius(
    client, db_session, seeded_lookups
):
    pharmacies = {
        pharmacy.nabp: pharmacy
        for pharmacy in (
            await db_session.scalars(
                select(PharmacyModel).where(
                    PharmacyModel.nabp.in_(["1234567", "7654321"])
                )
            )
        )
    }
    pharmacies["1234567"].latitude = 39.7817
    pharmacies["1234567"].longitude = -89.6501
    # Within the normal 10-mile default, but outside a zero-mile search.
    pharmacies["7654321"].latitude = 39.7917
    pharmacies["7654321"].longitude = -89.6501
    await db_session.flush()

    resp = await client.get(
        "/api/v1/pharmacies",
        params={"zipCode": "62704", "radius": 0},
        headers=AUTH,
    )

    assert resp.status_code == 200
    assert [pharmacy["nabp"] for pharmacy in resp.json()["data"]] == ["1234567"]


@pytest.mark.asyncio
async def test_get_pharmacy_rejects_invalid_us_zip_code(client, seeded_lookups):
    resp = await client.get(
        "/api/v1/pharmacies", params={"zipCode": "6270"}, headers=AUTH
    )

    assert resp.status_code == 400
    assert resp.json()["error"]["message"] == (
        "zipCode must be a valid five-digit U.S. ZIP code (for example, 62704)."
    )


@pytest.mark.asyncio
async def test_search_pharmacies_no_match(client, seeded_lookups):
    resp = await client.post(
        "/api/v1/pharmacies/search",
        json={"searchRequest": {"city": "Nowhere"}},
        headers=AUTH,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_search_pharmacies_missing_criteria(client, seeded_lookups):
    resp = await client.post(
        "/api/v1/pharmacies/search",
        json={"searchRequest": {"is24Hour": True}},
        headers=AUTH,
    )
    assert resp.status_code == 400
