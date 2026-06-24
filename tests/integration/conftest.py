from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.models.drug_model import DrugModel
from app.models.pharmacy_model import PharmacyModel
from app.models.prescriber_model import PrescriberModel
from app.utils.enums import BrandGeneric, Maintenance

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

AUTH = {"Authorization": "Bearer test-token"}


async def override_get_db():
    async with TestSession() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def disable_cache():
    original = settings.cache_enabled
    settings.cache_enabled = False
    yield
    settings.cache_enabled = original


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def seeded_lookups():
    async with TestSession() as session:
        session.add_all(
            [
                DrugModel(
                    ndc="00093721410",
                    gpi="39400010100310",
                    drug_name="Atorvastatin Calcium",
                    brand_generic=BrandGeneric.GENERIC,
                    maintenance=Maintenance.YES,
                    tier=1,
                    formulary_status="PREFERRED",
                    repackage_ind=False,
                ),
                DrugModel(
                    ndc="00093721420",
                    gpi="39400010100310",
                    drug_name="Atorvastatin Calcium HD",
                    brand_generic=BrandGeneric.GENERIC,
                    maintenance=Maintenance.YES,
                    tier=2,
                    formulary_status="PREFERRED",
                    repackage_ind=False,
                ),
                DrugModel(
                    ndc="00074312811",
                    gpi="27250030100120",
                    drug_name="Humira",
                    brand_generic=BrandGeneric.BRAND,
                    maintenance=Maintenance.NO,
                    tier=4,
                    formulary_status="NON_PREFERRED",
                    repackage_ind=False,
                ),
                DrugModel(
                    ndc="00000000000",
                    gpi="00000000000000",
                    drug_name="Deleted Drug",
                    brand_generic=BrandGeneric.GENERIC,
                    maintenance=Maintenance.NO,
                    repackage_ind=False,
                    is_deleted=True,
                ),
                PharmacyModel(
                    nabp="1234567",
                    npi="1023456789",
                    pharmacy_name="Main Street Pharmacy",
                    address_line1="100 Main St",
                    city="Springfield",
                    state="IL",
                    zip="62704",
                    phone="2175551234",
                    fax="2175555678",
                    is_24_hour=True,
                    in_network=True,
                ),
                PharmacyModel(
                    nabp="7654321",
                    npi="1987654321",
                    pharmacy_name="Downtown Drugs",
                    address_line1="55 Center Ave",
                    city="Chicago",
                    state="IL",
                    zip="60601",
                    phone="3125559876",
                    fax=None,
                    is_24_hour=False,
                    in_network=False,
                ),
                PrescriberModel(
                    npi="1112223334",
                    dea="AB1234567",
                    name="Dr. Jane Smith",
                    specialty="Cardiology",
                    address_line1="200 Health Ave",
                    city="Chicago",
                    state="IL",
                    zip="60601",
                    phone="3125551234",
                    fax="3125555678",
                ),
                PrescriberModel(
                    npi="5556667778",
                    dea=None,
                    name="Dr. John Doe",
                    specialty="Dermatology",
                    address_line1="300 Wellness Blvd",
                    city="Peoria",
                    state="IL",
                    zip="61602",
                    phone=None,
                    fax=None,
                ),
            ]
        )
        await session.commit()
