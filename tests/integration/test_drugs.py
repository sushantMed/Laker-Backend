from __future__ import annotations

import uuid

import pytest

from app.dependencies.auth import get_current_user
from app.main import app
from app.models.permission_model import UserPermissionModel
from app.models.user_model import UserModel
from app.utils.enums import BrandGeneric, Maintenance
from tests.integration.conftest import AUTH, _fake_current_user


@pytest.mark.asyncio
async def test_get_drug_by_ndc_success(client, seeded_lookups):
    resp = await client.get("/api/v1/drugs/00093721410", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["ndc"] == "00093721410"
    assert body["data"]["drugName"] == "Atorvastatin Calcium"
    assert body["data"]["brandGeneric"] == BrandGeneric.GENERIC.value


@pytest.mark.asyncio
async def test_get_drug_by_ndc_not_found(client, seeded_lookups):
    resp = await client.get("/api/v1/drugs/99999999999", headers=AUTH)
    assert resp.status_code == 404
    assert resp.json()["success"] is False


@pytest.mark.asyncio
async def test_get_drug_soft_deleted_not_returned(client, seeded_lookups):
    resp = await client.get("/api/v1/drugs/00000000000", headers=AUTH)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_drug_requires_auth(raw_client, seeded_lookups):
    resp = await raw_client.get("/api/v1/drugs/00093721410")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_drugs_by_gpi_success(client, seeded_lookups):
    resp = await client.get("/api/v1/drugs/gpi/39400010100310", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["pagination"]["total"] == 2
    assert {d["ndc"] for d in body["data"]} == {"00093721410", "00093721420"}


@pytest.mark.asyncio
async def test_get_drugs_by_gpi_pagination(client, seeded_lookups):
    resp = await client.get(
        "/api/v1/drugs/gpi/39400010100310",
        params={"page": 1, "pageSize": 1},
        headers=AUTH,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 1
    assert body["pagination"]["total"] == 2
    assert body["pagination"]["totalPages"] == 2
    assert body["pagination"]["hasNext"] is True


@pytest.mark.asyncio
async def test_get_drugs_by_gpi_not_found(client, seeded_lookups):
    resp = await client.get("/api/v1/drugs/gpi/11111111111111", headers=AUTH)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_search_drugs_by_name(client, seeded_lookups):
    resp = await client.post(
        "/api/v1/drugs/search",
        json={"searchRequest": {"name": "Atorvastatin"}},
        headers=AUTH,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["pagination"]["total"] == 2


@pytest.mark.asyncio
async def test_search_drugs_by_brand_generic(client, seeded_lookups):
    resp = await client.post(
        "/api/v1/drugs/search",
        json={"searchRequest": {"brandGeneric": BrandGeneric.BRAND.value}},
        headers=AUTH,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["pagination"]["total"] == 1
    assert body["data"][0]["drugName"] == "Humira"


@pytest.mark.asyncio
async def test_search_drugs_by_ndc(client, seeded_lookups):
    resp = await client.post(
        "/api/v1/drugs/search",
        json={"searchRequest": {"ndc": "00074312811"}},
        headers=AUTH,
    )
    assert resp.status_code == 200
    assert resp.json()["data"][0]["drugName"] == "Humira"


@pytest.mark.asyncio
async def test_search_drugs_by_gpi_maintenance_and_tier(client, seeded_lookups):
    resp = await client.post(
        "/api/v1/drugs/search",
        json={
            "searchRequest": {
                "gpi": "39400010100310",
                "maintenance": Maintenance.YES.value,
                "tier": 1,
            }
        },
        headers=AUTH,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["pagination"]["total"] == 1
    assert body["data"][0]["ndc"] == "00093721410"


@pytest.mark.asyncio
async def test_search_drugs_without_drug_grant_is_forbidden(client, seeded_lookups):
    """`client`'s user holds every screen, so swap in one granted another
    screen entirely."""

    async def _user_without_drug_grant() -> UserModel:
        return UserModel(
            id=uuid.uuid4(),
            email="nodrugs@example.com",
            first_name="No",
            last_name="Drugs",
            hashed_password="x",
            status="ACTIVE",
            grants=[
                UserPermissionModel(
                    pername="Memeber Screen", viewperm="Y", saveperm="Y"
                )
            ],
        )

    app.dependency_overrides[get_current_user] = _user_without_drug_grant
    try:
        resp = await client.post(
            "/api/v1/drugs/search",
            json={"searchRequest": {"name": "Atorvastatin"}},
            headers=AUTH,
        )
    finally:
        app.dependency_overrides[get_current_user] = _fake_current_user

    assert resp.status_code == 403
    body = resp.json()
    assert body["success"] is False
    assert body["message"] == "Missing permission: drug:view"


@pytest.mark.asyncio
async def test_search_drugs_sorted_desc(client, seeded_lookups):
    resp = await client.post(
        "/api/v1/drugs/search",
        json={
            "searchRequest": {"name": "Atorvastatin"},
            "sort": {"sortBy": "ndc", "sortDir": "DESC"},
        },
        headers=AUTH,
    )
    assert resp.status_code == 200
    ndcs = [d["ndc"] for d in resp.json()["data"]]
    assert ndcs == ["00093721420", "00093721410"]


@pytest.mark.asyncio
async def test_search_drugs_no_match(client, seeded_lookups):
    resp = await client.post(
        "/api/v1/drugs/search",
        json={"searchRequest": {"name": "Nonexistent"}},
        headers=AUTH,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"] == []
    assert body["pagination"]["total"] == 0


@pytest.mark.asyncio
async def test_search_drugs_missing_criteria(client, seeded_lookups):
    resp = await client.post(
        "/api/v1/drugs/search",
        json={"searchRequest": {}},
        headers=AUTH,
    )
    assert resp.status_code == 400
