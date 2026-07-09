from __future__ import annotations

import uuid
from datetime import date
from typing import AsyncGenerator

import pytest  #type: ignore
import pytest_asyncio  #type: ignore
from httpx import ASGITransport, AsyncClient  #type: ignore
from sqlalchemy import event  #type: ignore
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  #type: ignore
from app.models.member_model import MemberModel
from app.utils.enums import Gender, CoverageType
from app.core.config import settings
from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.api.v1.auth import bearer
from app.models.claim_model import ClaimModel
from app.models.drug_model import DrugModel
from app.models.pharmacy_model import PharmacyModel
from app.models.prescriber_model import PrescriberModel
from app.utils.enums import BrandGeneric, Maintenance


# ── Test database ─────────────────────────────────────────────────────────────

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
AUTH = {"Authorization": "Bearer test-token"}

engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _):
    dbapi_conn.execute("PRAGMA foreign_keys=OFF")

TestSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(conn, expire_on_commit=False)
        await conn.begin_nested()
        try:
            yield session
        finally:
            await session.close()
            await conn.rollback()


# ── Dependency overrides ──────────────────────────────────────────────────────

def _make_db_override(session: AsyncSession):
    async def _override():
        yield session
    return _override


async def _noop_bearer():
    return None


# ── Settings override ─────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def disable_cache():
    original = settings.cache_enabled
    settings.cache_enabled = False
    yield
    settings.cache_enabled = original


# ── HTTP client fixtures ──────────────────────────────────────────────────────

BASE_PATH = "/api/v1"
VALID_AUTH_TOKEN = "Bearer test-token"

def _auth_header() -> dict[str, str]:
    return {"Authorization": VALID_AUTH_TOKEN}


@pytest_asyncio.fixture()
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Bearer bypassed — for claim/member/pharmacy/drug tests."""
    app.dependency_overrides[get_db] = _make_db_override(db_session)
    app.dependency_overrides[bearer] = _noop_bearer

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def raw_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Real bearer — for auth endpoint tests."""
    app.dependency_overrides[get_db] = _make_db_override(db_session)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Helpers / factories ───────────────────────────────────────────────────────

def _make_claim(
    *,
    member_id: str = "MBR001",
    auth_num: str | None = None,
    rx_number: str = "RX100",
    drug_name: str = "Lipitor",
    ndc: str = "00071015423",
    date_filled: date = date(2024, 3, 15),
    date_written: date | None = date(2024, 3, 10),
    pharmacy_npi: str | None = "1234567890",
    pharmacy_name: str | None = "Health Pharmacy",
    prescriber_npi: str | None = "9876543210",
    prescriber_name: str | None = "Dr. Smith",
    is_test_claim: bool = False,
    plan_id: str | None = None,
    ingredient_cost: float = 50.0,
    dispensing_fee: float = 2.5,
    copay: float = 10.0,
    total_paid: float = 62.5,
) -> ClaimModel:
    unique_suffix = uuid.uuid4().hex[:8]
    return ClaimModel(
        id=uuid.uuid4(),
        claim_id=f"CLM-{unique_suffix}",
        auth_num=auth_num or f"AUTH-{unique_suffix}",
        member_id=member_id,
        rx_number=rx_number,
        drug_name=drug_name,
        ndc=ndc,
        date_filled=date_filled,
        date_written=date_written,
        pharmacy_npi=pharmacy_npi,
        pharmacy_name=pharmacy_name,
        prescriber_npi=prescriber_npi,
        prescriber_name=prescriber_name,
        is_test_claim=is_test_claim,
        plan_id=plan_id,
        ingredient_cost=ingredient_cost,
        dispensing_fee=dispensing_fee,
        copay=copay,
        total_paid=total_paid,
    )


def _make_member(
    *,
    member_id: str,
    first_name: str = "Test",
    last_name: str = "User",
    date_of_birth: date = date(1990, 1, 1),
    person_code: str = "01",
    rel_code: str = "01",
    start_date: date = date(2020, 1, 1),
    end_date: date = date(2099, 12, 31),
) -> MemberModel:
    return MemberModel(
        id=uuid.uuid4(),
        member_id=member_id,
        first_name=first_name,
        last_name=last_name,
        date_of_birth=date_of_birth,
        person_code=person_code,
        rel_code=rel_code,
        start_date=start_date,
        end_date=end_date,
    )

async def _seed(session: AsyncSession, *claims: ClaimModel) -> list[ClaimModel]:
    session.add_all(claims)
    await session.flush()
    return list(claims)


@pytest_asyncio.fixture()
async def seeded_lookups(db_session: AsyncSession):
    """Seeds reference data (drugs, pharmacies, prescribers) into the test transaction."""
    db_session.add_all([
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
    ])
    await db_session.flush()
