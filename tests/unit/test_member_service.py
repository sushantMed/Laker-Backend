from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import (
    DuplicateSpouseException,
    InvalidFamilyRelationshipException,
    MemberNotFoundException,
    PlanNotFoundException,
)
from app.models.member_model import MemberModel
from app.models.plan_model import PlanModel
from app.schemas.member_schema import (
    AddFamilyMemberRequest,
    EligibilityResponse,
    FamilyMembersRequest,
    MemberAddressSchema,
    MemberDetail,
    MemberSearch,
    MemberSearchRequest,
    MemberSummary,
    PlanSummary,
)
from app.services import member_service as member_service_module
from app.services.member_service import (
    MemberService,
    _address_schema,
    _calculate_age,
    _plan_summary,
    _to_member_detail,
    _to_member_summary,
)
from app.utils.enums import CoverageType, FamilyRole, Gender, MemberStatus
from app.utils.pagination import PaginationRequest


def make_plan(
    plan_id: str = "PLN001",
    carrier: str = "Acme Health",
    group_name: str | None = "Group A",
    group_number: str | None = "GRP-1",
    rx_bin: str | None = "123456",
    rx_pcn: str | None = "PCN1",
) -> PlanModel:
    return PlanModel(
        id=uuid.uuid4(),
        plan_id=plan_id,
        carrier=carrier,
        group_name=group_name,
        group_number=group_number,
        rx_bin=rx_bin,
        rx_pcn=rx_pcn,
    )


def make_member(
    member_id: str = "MBR001",
    *,
    subscriber_member_id: str | None = None,
    first_name: str = "John",
    last_name: str = "Doe",
    mi: str | None = "A",
    date_of_birth: date = date(1980, 1, 1),
    gender: Gender | None = Gender.MALE,
    ssn: str | None = "123-45-6789",
    phone: str | None = "5551234567",
    email: str | None = "john@example.com",
    language_preference: str | None = "EN",
    insured_id: str | None = "INS001",
    person_code: str = "01",
    family_position: str | None = "01",
    rel_code: str = "01",
    laker_pc: str | None = "LPC1",
    prev_card_id: str | None = None,
    cov_type: CoverageType | None = CoverageType.FAMILY,
    start_date: date = date(2020, 1, 1),
    end_date: date = date(2030, 1, 1),
    plan_id: str | None = "PLN001",
    plan: PlanModel | None = None,
) -> MemberModel:
    member = MemberModel(
        id=uuid.uuid4(),
        member_id=member_id,
        subscriber_member_id=subscriber_member_id,
        first_name=first_name,
        last_name=last_name,
        mi=mi,
        date_of_birth=date_of_birth,
        gender=gender,
        ssn=ssn,
        phone=phone,
        email=email,
        language_preference=language_preference,
        insured_id=insured_id,
        person_code=person_code,
        family_position=family_position,
        rel_code=rel_code,
        laker_pc=laker_pc,
        prev_card_id=prev_card_id,
        cov_type=cov_type,
        start_date=start_date,
        end_date=end_date,
        plan_id=plan_id,
    )
    member.plan = plan
    member.address = None
    return member


def make_add_request(
    *,
    first_name: str = "Jane",
    last_name: str = "Doe",
    date_of_birth: date = date(1985, 6, 1),
    rel_code: str = "02",
    start_date: date = date(2020, 1, 1),
    end_date: date = date(2030, 1, 1),
    plan_id: str | None = None,
    cov_type: CoverageType | None = CoverageType.SPOUSE,
    address: MemberAddressSchema | None = None,
) -> AddFamilyMemberRequest:
    return AddFamilyMemberRequest(
        firstName=first_name,
        lastName=last_name,
        dateOfBirth=date_of_birth,
        relCode=rel_code,
        startDate=start_date,
        endDate=end_date,
        planId=plan_id,
        covType=cov_type,
        address=address,
    )


@pytest.fixture
def service() -> MemberService:
    svc = MemberService(session=AsyncMock())
    svc._repo = AsyncMock()
    svc._plan_repo = AsyncMock()
    svc._cache = AsyncMock()
    svc._session = AsyncMock()
    return svc


def test_calculate_age_before_birthday_this_year():
    dob = date(date.today().year - 30, 12, 31)
    assert _calculate_age(dob) == "29"


def test_calculate_age_already_had_birthday():
    dob = date(date.today().year - 40, 1, 1)
    assert _calculate_age(dob) == "40"


def test_plan_summary_returns_none_for_none():
    assert _plan_summary(None) is None


def test_plan_summary_maps_fields():
    summary = _plan_summary(make_plan())
    assert isinstance(summary, PlanSummary)
    assert summary.plan_id == "PLN001"
    assert summary.carrier == "Acme Health"
    assert summary.group_name == "Group A"
    assert summary.rx_bin == "123456"


def test_address_schema_returns_none_for_none():
    assert _address_schema(None) is None


def test_address_schema_maps_fields():
    address = type(
        "Addr",
        (),
        {
            "address1": "1 Main St",
            "address2": "Apt 2",
            "city": "Springfield",
            "state": "IL",
            "zip": "62704",
        },
    )()
    schema = _address_schema(address)
    assert isinstance(schema, MemberAddressSchema)
    assert schema.address1 == "1 Main St"
    assert schema.city == "Springfield"
    assert schema.state == "IL"


def test_to_member_detail_maps_all_fields():
    member = make_member(plan=make_plan())
    detail = _to_member_detail(member)

    assert isinstance(detail, MemberDetail)
    assert detail.member_id == "MBR001"
    assert detail.first_name == "John"
    assert detail.role == FamilyRole.CARDHOLDER
    assert detail.status == MemberStatus.ACTIVE
    assert detail.plan is not None
    assert detail.plan.carrier == "Acme Health"
    assert detail.address is None


def test_to_member_summary_maps_carrier_from_plan():
    member = make_member(plan=make_plan(carrier="Globex"))
    summary = _to_member_summary(member)

    assert isinstance(summary, MemberSummary)
    assert summary.member_id == "MBR001"
    assert summary.carrier == "Globex"
    assert summary.role == FamilyRole.CARDHOLDER


def test_to_member_summary_carrier_none_without_plan():
    member = make_member(plan=None)
    summary = _to_member_summary(member)
    assert summary.carrier is None


async def test_get_member_by_id_returns_cached(service: MemberService):
    cached = _to_member_detail(make_member(plan=make_plan()))
    service._cache.get.return_value = cached

    result = await service.get_member_by_id("MBR001")

    assert result is cached
    service._cache.get.assert_awaited_once()
    service._repo.get_by_member_id.assert_not_called()


async def test_get_member_by_id_fetches_and_caches_on_miss(service: MemberService):
    service._cache.get.return_value = None
    member = make_member(plan=make_plan())
    service._repo.get_by_member_id.return_value = member

    result = await service.get_member_by_id("MBR001")

    assert result.member_id == "MBR001"
    service._repo.get_by_member_id.assert_awaited_once_with("MBR001")
    service._cache.set.assert_awaited_once()


async def test_get_member_by_id_raises_when_missing(service: MemberService):
    service._cache.get.return_value = None
    service._repo.get_by_member_id.return_value = None

    with pytest.raises(MemberNotFoundException) as exc:
        await service.get_member_by_id("NOPE")

    assert exc.value.status_code == 404
    service._cache.set.assert_not_called()


async def test_search_members_returns_paged_response(service: MemberService):
    service._cache.get.return_value = None
    members = [make_member(member_id="MBR001"), make_member(member_id="MBR002")]
    service._repo.search.return_value = (members, 2)
    request = MemberSearchRequest(searchRequest=MemberSearch(last_name="Doe"))

    result = await service.search_members(request)

    assert len(result.data) == 2
    assert result.pagination.total == 2
    service._cache.set.assert_awaited_once()


async def test_search_members_returns_cached(service: MemberService):
    request = MemberSearchRequest(searchRequest=MemberSearch(last_name="Doe"))
    cached = object()
    service._cache.get.return_value = cached

    result = await service.search_members(request)

    assert result is cached
    service._repo.search.assert_not_called()


async def test_search_members_raises_when_empty(service: MemberService):
    service._cache.get.return_value = None
    service._repo.search.return_value = ([], 0)
    request = MemberSearchRequest(searchRequest=MemberSearch(last_name="Nobody"))

    result = await service.search_members(request)

    assert result.data == []


async def test_get_eligibility_returns_cached(service: MemberService):
    cached = EligibilityResponse(
        memberId="MBR001",
        status=MemberStatus.ACTIVE,
        startDate=date(2020, 1, 1),
        endDate=date(2030, 1, 1),
    )
    service._cache.get.return_value = cached

    result = await service.get_eligibility("MBR001")

    assert result is cached
    service._repo.get_by_member_id.assert_not_called()


async def test_get_eligibility_fetches_on_miss(service: MemberService):
    service._cache.get.return_value = None
    service._repo.get_by_member_id.return_value = make_member()

    result = await service.get_eligibility("MBR001")

    assert isinstance(result, EligibilityResponse)
    assert result.member_id == "MBR001"
    assert result.status == MemberStatus.ACTIVE
    service._cache.set.assert_awaited_once()


async def test_get_eligibility_raises_when_missing(service: MemberService):
    service._cache.get.return_value = None
    service._repo.get_by_member_id.return_value = None

    with pytest.raises(MemberNotFoundException):
        await service.get_eligibility("NOPE")


async def test_get_family_raises_when_subscriber_missing(service: MemberService):
    service._repo.get_by_member_id.return_value = None
    request = PaginationRequest()

    with pytest.raises(MemberNotFoundException):
        await service.get_family("NOPE", request)


async def test_get_family_raises_when_not_cardholder(service: MemberService):
    service._repo.get_by_member_id.return_value = make_member(rel_code="03")
    request = PaginationRequest()

    with pytest.raises(InvalidFamilyRelationshipException):
        await service.get_family("MBR001", request)


async def test_get_family_returns_paged_response(service: MemberService):
    subscriber = make_member(member_id="MBR001", rel_code="01")
    service._repo.get_by_member_id.return_value = subscriber
    service._cache.get.return_value = None
    members = [subscriber, make_member(member_id="MBR002", rel_code="03")]
    service._repo.get_family_members.return_value = (members, 2)
    request = FamilyMembersRequest()

    result = await service.get_family("MBR001", request)

    assert len(result.data) == 2
    assert result.pagination.total == 2


async def test_add_family_member_raises_when_subscriber_missing(service: MemberService):
    service._repo.get_by_member_id.return_value = None

    with pytest.raises(MemberNotFoundException):
        await service.add_family_member("NOPE", make_add_request())


async def test_add_family_member_raises_when_not_cardholder(service: MemberService):
    service._repo.get_by_member_id.return_value = make_member(rel_code="03")

    with pytest.raises(InvalidFamilyRelationshipException):
        await service.add_family_member("MBR001", make_add_request())


async def test_add_family_member_raises_on_duplicate_spouse(service: MemberService):
    service._repo.get_by_member_id.return_value = make_member(rel_code="01")
    service._repo.get_spouse_count.return_value = 1

    with pytest.raises(DuplicateSpouseException):
        await service.add_family_member("MBR001", make_add_request(rel_code="02"))


async def test_add_family_member_raises_when_plan_missing(service: MemberService):
    service._repo.get_by_member_id.return_value = make_member(rel_code="01")
    service._repo.get_spouse_count.return_value = 0
    service._plan_repo.get_by_plan_id.return_value = None

    request = make_add_request(rel_code="03", plan_id="MISSING")

    with pytest.raises(PlanNotFoundException):
        await service.add_family_member("MBR001", request)


async def test_add_family_member_success_generates_codes(service: MemberService):
    service._repo.get_by_member_id.return_value = make_member(rel_code="01")
    service._repo.get_spouse_count.return_value = 0
    service._repo.get_max_person_code.return_value = 1
    service._repo.get_max_family_position.return_value = 1
    saved = make_member(member_id="MBR999", rel_code="02", person_code="02")
    service._repo.add.return_value = saved

    request = make_add_request(rel_code="02")
    result = await service.add_family_member("MBR001", request)

    assert isinstance(result, MemberDetail)
    added = service._repo.add.await_args.args[0]
    assert added.person_code == "02"
    assert added.family_position == "02"
    assert added.subscriber_member_id == "MBR001"
    service._session.commit.assert_awaited_once()
    service._cache.delete_pattern.assert_awaited()


def test_generate_member_id_format():
    from app.repositories.member_repository import MemberRepository

    member_id = MemberRepository.generate_member_id()
    assert member_id.startswith("MBR")
    assert len(member_id) == 6


def test_service_uses_member_namespace(monkeypatch):
    captured = {}

    class FakeCache:
        def __init__(self, namespace: str) -> None:
            captured["namespace"] = namespace

    monkeypatch.setattr(member_service_module, "CacheService", FakeCache)
    MemberService(session=AsyncMock())

    assert captured["namespace"] == "member"
