from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.netlist_model import NetListModel
from app.models.pharmacy_model import PharmacyModel
from app.models.zip_code_model import ZipCodeModel
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
    # Distance is derived from the pharmacy's own ZIP centroid (joined via
    # its first five digits), not any lat/long stored on the pharmacy row.
    # 62705 sits ~8.2 miles north of the seeded 62704 centroid -- inside the
    # default 10-mile radius but outside a 5-mile search.
    db_session.add(
        ZipCodeModel(zip="62705", latitude=39.9, longitude=-89.6501, citytype="D")
    )
    pharmacy = await db_session.scalar(
        select(PharmacyModel).where(PharmacyModel.nabp == "7654321")
    )
    pharmacy.zip = "62705"
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
    # 62706 sits ~0.7 miles from the seeded 62704 centroid -- within the
    # normal 10-mile default, but outside a zero-mile search.
    db_session.add(
        ZipCodeModel(zip="62706", latitude=39.7917, longitude=-89.6501, citytype="D")
    )
    pharmacy = await db_session.scalar(
        select(PharmacyModel).where(PharmacyModel.nabp == "7654321")
    )
    pharmacy.zip = "62706"
    await db_session.flush()

    resp = await client.get(
        "/api/v1/pharmacies",
        params={"zipCode": "62704", "radius": 0},
        headers=AUTH,
    )

    assert resp.status_code == 200
    assert [pharmacy["nabp"] for pharmacy in resp.json()["data"]] == ["1234567"]


@pytest.mark.asyncio
async def test_get_pharmacies_by_zip_excludes_out_of_network_pharmacy(
    client, db_session, seeded_lookups
):
    """A pharmacy near the search center is excluded unless NETLIST lists its
    NABP (type 'P') or its affiliation code (type 'C')."""
    pharmacy = await db_session.scalar(
        select(PharmacyModel).where(PharmacyModel.nabp == "1234567")
    )
    pharmacy.affiliation_code = None
    await db_session.execute(
        NetListModel.__table__.delete().where(NetListModel.value == "1234567")
    )
    await db_session.flush()

    resp = await client.get(
        "/api/v1/pharmacies",
        params={"zipCode": "62704", "radius": 5},
        headers=AUTH,
    )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_pharmacies_by_zip_matches_via_affiliation_code(
    client, db_session, seeded_lookups
):
    """A pharmacy can also qualify via its chain affiliation code listed in
    NETLIST under type 'C', even when its own NABP isn't listed."""
    pharmacy = await db_session.scalar(
        select(PharmacyModel).where(PharmacyModel.nabp == "1234567")
    )
    pharmacy.affiliation_code = "CHN"
    await db_session.execute(
        NetListModel.__table__.delete().where(NetListModel.value == "1234567")
    )
    db_session.add(NetListModel(net_num=1, line_num=3, type="C", value="CHN"))
    await db_session.flush()

    resp = await client.get(
        "/api/v1/pharmacies",
        params={"zipCode": "62704", "radius": 5},
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
        "zipCode must be a valid U.S. ZIP or ZIP+4 code (for example, 62704 or 62704-1234)."
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
