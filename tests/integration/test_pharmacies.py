from __future__ import annotations

import pytest

from tests.integration.conftest import AUTH


@pytest.mark.asyncio
async def test_get_pharmacy_by_nabp_success(client, seeded_lookups):
    resp = await client.get("/api/v1/pharmacies/1234567", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["nabp"] == "1234567"
    assert body["data"]["address"] == "100 Main St, Springfield, IL 62704"
    assert body["data"]["is24Hour"] is True


@pytest.mark.asyncio
async def test_get_pharmacy_by_nabp_not_found(client, seeded_lookups):
    resp = await client.get("/api/v1/pharmacies/0000000", headers=AUTH)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_pharmacy_requires_auth(raw_client, seeded_lookups):
    resp = await raw_client.get("/api/v1/pharmacies/1234567")
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
async def test_search_pharmacies_out_of_network_only(client, seeded_lookups):
    resp = await client.post(
        "/api/v1/pharmacies/search",
        json={"searchRequest": {"state": "IL", "inNetwork": False}},
        headers=AUTH,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["pagination"]["total"] == 1
    assert body["data"][0]["pharmacyName"] == "Downtown Drugs"


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
