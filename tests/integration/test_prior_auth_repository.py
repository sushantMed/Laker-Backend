from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.prior_auth_repository import (
    PriorAuthRepository,
    _person_code_clause,
    _status_clause,
)
from app.utils.enums import PAStatus
from tests.integration.test_prior_auth_endpoints import make_pa

TODAY = date.today()


@pytest_asyncio.fixture()
async def repo(db_session: AsyncSession) -> PriorAuthRepository:
    db_session.add_all(
        [
            make_pa(3001, genname="ADALIMUMAB"),
            make_pa(3002, subscribernum="INS002", personcodes="02", ndc="00093721410"),
            make_pa(3003, action=None, prescriberid="5556667778"),
            make_pa(3004, action="D", denial="03", effdate=date(2026, 3, 1)),
            make_pa(3005, termdate=TODAY - timedelta(days=1)),
        ]
    )
    await db_session.flush()
    return PriorAuthRepository(db_session)


@pytest.mark.asyncio
async def test_get_by_authnum(repo: PriorAuthRepository):
    found = await repo.get_by_authnum(Decimal(3001))

    assert found is not None
    assert found.genname == "ADALIMUMAB"


@pytest.mark.asyncio
async def test_get_by_authnum_missing(repo: PriorAuthRepository):
    assert await repo.get_by_authnum(Decimal(9999)) is None


@pytest.mark.asyncio
async def test_next_authnum_follows_highest(repo: PriorAuthRepository):
    assert await repo.next_authnum() == Decimal(3006)


@pytest.mark.asyncio
async def test_next_authnum_on_empty_table(db_session: AsyncSession):
    assert await PriorAuthRepository(db_session).next_authnum() == Decimal(1)


@pytest.mark.asyncio
async def test_add_flushes_row(db_session: AsyncSession):
    repo = PriorAuthRepository(db_session)

    added = await repo.add(make_pa(4001))

    assert await repo.get_by_authnum(Decimal(4001)) is added


@pytest.mark.asyncio
async def test_search_by_partial_pa_id(repo: PriorAuthRepository):
    items, total = await repo.search(pa_id="300")

    assert total == 5
    assert len(items) == 5


@pytest.mark.asyncio
async def test_search_by_insured_id(repo: PriorAuthRepository):
    items, total = await repo.search(insured_id="INS002")

    assert total == 1
    assert items[0].authnum == Decimal(3002)


@pytest.mark.asyncio
async def test_search_by_subscriber_num_is_partial(repo: PriorAuthRepository):
    _, total = await repo.search(subscriber_num="INS")

    assert total == 5


@pytest.mark.asyncio
async def test_search_by_ndc(repo: PriorAuthRepository):
    _, total = await repo.search(ndc="00093721410")

    assert total == 1


@pytest.mark.asyncio
async def test_search_by_prescriber_npi(repo: PriorAuthRepository):
    items, total = await repo.search(prescriber_npi="5556667778")

    assert total == 1
    assert items[0].authnum == Decimal(3003)


@pytest.mark.asyncio
async def test_search_by_drug_name_on_generic_name(repo: PriorAuthRepository):
    _, total = await repo.search(drug_name="adalimumab")

    assert total == 5


@pytest.mark.asyncio
async def test_search_by_drug_name_on_catalogue(
    repo: PriorAuthRepository, seeded_lookups
):
    items, _ = await repo.search(drug_name="Atorvastatin Calcium")

    assert {int(pa.authnum) for pa in items} == {3002}


@pytest.mark.asyncio
async def test_search_sorts_descending(repo: PriorAuthRepository):
    items, _ = await repo.search(sort_by="paId", sort_dir="desc")

    assert [int(pa.authnum) for pa in items] == [3005, 3004, 3003, 3002, 3001]


@pytest.mark.asyncio
async def test_search_sorts_ascending_by_default(repo: PriorAuthRepository):
    items, _ = await repo.search(sort_by="paId")

    assert [int(pa.authnum) for pa in items] == [3001, 3002, 3003, 3004, 3005]


@pytest.mark.asyncio
async def test_search_unknown_sort_column_falls_back_to_eff_date(
    repo: PriorAuthRepository,
):
    items, _ = await repo.search(sort_by="nonsense")

    assert int(items[0].authnum) == 3004


@pytest.mark.asyncio
async def test_search_paginates(repo: PriorAuthRepository):
    items, total = await repo.search(sort_by="paId", page=2, page_size=2)

    assert total == 5
    assert [int(pa.authnum) for pa in items] == [3003, 3004]


@pytest.mark.asyncio
async def test_search_returns_nothing_for_unmatched_filter(repo: PriorAuthRepository):
    items, total = await repo.search(ndc="99999999999")

    assert items == []
    assert total == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status",
    [PAStatus.AUTHORIZED, PAStatus.DECLINED, PAStatus.PENDING, PAStatus.EXPIRED],
)
async def test_status_clause_compiles_for_every_status(status):
    clause = _status_clause(status, TODAY)

    assert str(clause)


def test_person_code_clause_pads_with_commas():
    assert ",02," in str(_person_code_clause("02").right.value)
