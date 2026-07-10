from __future__ import annotations

import pytest

from tests.integration.conftest import AUTH


@pytest.mark.asyncio
async def test_get_prescriber_by_npi_success(client, seeded_lookups):
    resp = await client.get("/api/v1/prescribers/1112223334", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["npi"] == "1112223334"
    assert body["data"]["name"] == "Dr. Jane Smith"
    assert body["data"]["address"] == "200 Health Ave, Chicago, IL 60601"


@pytest.mark.asyncio
async def test_get_prescriber_by_npi_not_found(client, seeded_lookups):
    resp = await client.get("/api/v1/prescribers/0000000000", headers=AUTH)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_prescriber_requires_auth(raw_client, seeded_lookups):
    resp = await raw_client.get("/api/v1/prescribers/1112223334")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_search_prescribers_by_specialty(client, seeded_lookups):
    resp = await client.post(
        "/api/v1/prescribers/search",
        json={"searchRequest": {"specialty": "Cardiology"}},
        headers=AUTH,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["pagination"]["total"] == 1
    assert body["data"][0]["name"] == "Dr. Jane Smith"


@pytest.mark.asyncio
async def test_search_prescribers_by_name(client, seeded_lookups):
    resp = await client.post(
        "/api/v1/prescribers/search",
        json={"searchRequest": {"name": "Dr."}},
        headers=AUTH,
    )
    assert resp.status_code == 200
    assert resp.json()["pagination"]["total"] == 2


@pytest.mark.asyncio
async def test_search_prescribers_by_npi_and_dea(client, seeded_lookups):
    resp = await client.post(
        "/api/v1/prescribers/search",
        json={"searchRequest": {"npi": "1112223334", "dea": "AB1234567"}},
        headers=AUTH,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["pagination"]["total"] == 1
    assert body["data"][0]["name"] == "Dr. Jane Smith"


@pytest.mark.asyncio
async def test_search_prescribers_by_city_and_state(client, seeded_lookups):
    resp = await client.post(
        "/api/v1/prescribers/search",
        json={"searchRequest": {"city": "Peoria", "state": "IL"}},
        headers=AUTH,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["pagination"]["total"] == 1
    assert body["data"][0]["name"] == "Dr. John Doe"


@pytest.mark.asyncio
async def test_search_prescribers_no_match(client, seeded_lookups):
    resp = await client.post(
        "/api/v1/prescribers/search",
        json={"searchRequest": {"name": "Nobody"}},
        headers=AUTH,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_search_prescribers_missing_criteria(client, seeded_lookups):
    resp = await client.post(
        "/api/v1/prescribers/search",
        json={"searchRequest": {}},
        headers=AUTH,
    )
    assert resp.status_code == 400
