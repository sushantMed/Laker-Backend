from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import (
    DrugNotFoundException,
    InvalidStatusTransitionException,
    MemberNotFoundException,
    PrescriberNotFoundException,
    PriorAuthNotEditableException,
    PriorAuthNotFoundException,
)
from app.models.drug_model import DrugModel
from app.models.member_model import MemberModel
from app.models.plan_model import PlanModel
from app.models.prescriber_model import PrescriberModel
from app.models.prior_auth_model import PriorAuthModel
from app.schemas.prior_auth_schema import (
    CreatePARequest,
    PAByEntityQuery,
    PASearch,
    PASearchByMemberPath,
    PASearchRequest,
    PASearchRequestByMemberPath,
    PatchPARequest,
    UpdatePARequest,
)
from app.services.prior_auth_service import (
    PriorAuthService,
    _apply_status,
    _audit_user,
    _drug_name,
    _expire_on_or_before,
    _format_pa_id,
    _parse_pa_id,
    _person_codes,
    _provider,
    _References,
    _require_valid_transition,
    _stamp_change,
    _to_detail,
    _to_int,
    _to_search_result,
)
from app.utils.enums import (
    BrandGeneric,
    Maintenance,
    PAStatus,
    derive_pa_status,
    pa_action_for_status,
)

TODAY = date(2026, 8, 10)


def make_pa(**overrides) -> PriorAuthModel:
    values = {
        "authnum": Decimal(1001),
        "subscribernum": "INS001",
        "groupnum": "GRP001",
        "personcodes": "01",
        "effdate": date(2026, 1, 1),
        "termdate": date(2027, 1, 1),
        "providerid": "2400214",
        "prescriberid": "1326367012",
        "ndc": "00074580302",
        "gpi": "66000015100315",
        "bg": "B",
        "action": "A",
        "genname": "ADALIMUMAB",
        "manualgenname": None,
        "authby": "DR. ANITA PATEL",
        "denial": None,
        "reasoncode": "SPECIALTY",
        "notes": "notes",
        "maxscripts": Decimal(13),
        "daysold": Decimal(3),
    }
    values.update(overrides)
    return PriorAuthModel(**values)


def make_member(
    member_id: str = "MBR001",
    insured_id: str | None = "INS001",
    person_code: str = "01",
    plan: PlanModel | None = None,
) -> MemberModel:
    return MemberModel(
        member_id=member_id,
        first_name="Carlos",
        last_name="Martinez",
        date_of_birth=date(1978, 4, 12),
        person_code=person_code,
        rel_code="01",
        start_date=date(2023, 1, 1),
        end_date=date(2027, 12, 31),
        insured_id=insured_id,
        plan=plan,
    )


def make_drug(ndc: str = "00074580302", name: str = "HUMIRA SOLN 40MG") -> DrugModel:
    return DrugModel(
        ndc=ndc,
        gpi="66000015100315",
        drug_name=name,
        brand_generic=BrandGeneric.BRAND,
        maintenance=Maintenance.YES,
        repackage_ind=False,
    )


def make_prescriber(npi: str = "1326367012") -> PrescriberModel:
    return PrescriberModel(
        npi=npi,
        dea="AP1234567",
        name="DR. ANITA PATEL",
        specialty="Rheumatology",
        address_line1="1420 N Lake Shore Dr",
        city="Chicago",
        state="IL",
        zip="60610",
    )


@pytest.fixture
def service() -> PriorAuthService:
    svc = PriorAuthService(session=AsyncMock())
    svc._repo = AsyncMock()
    svc._member_repo = AsyncMock()
    svc._drug_repo = AsyncMock()
    svc._prescriber_repo = AsyncMock()
    svc._session = AsyncMock()
    return svc


@pytest.mark.parametrize(
    ("action", "denial", "term_date", "expected"),
    [
        ("A", None, date(2027, 1, 1), PAStatus.AUTHORIZED),
        ("A", None, None, PAStatus.AUTHORIZED),
        ("a", None, date(2027, 1, 1), PAStatus.AUTHORIZED),
        (" A ", "", date(2027, 1, 1), PAStatus.AUTHORIZED),
        ("A", None, date(2026, 8, 9), PAStatus.EXPIRED),
        ("A", None, TODAY, PAStatus.AUTHORIZED),
        ("D", None, date(2027, 1, 1), PAStatus.DECLINED),
        ("A", "03", date(2027, 1, 1), PAStatus.DECLINED),
        (None, None, date(2027, 1, 1), PAStatus.PENDING),
        ("", None, None, PAStatus.PENDING),
        ("X", None, None, PAStatus.PENDING),
    ],
)
def test_derive_pa_status(action, denial, term_date, expected):
    assert derive_pa_status(action, denial, term_date, TODAY) is expected


def test_derive_pa_status_defaults_to_today():
    assert derive_pa_status("A", None, date(2000, 1, 1)) is PAStatus.EXPIRED


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (PAStatus.AUTHORIZED, "A"),
        (PAStatus.DECLINED, "D"),
        (PAStatus.PENDING, None),
        (PAStatus.EXPIRED, "A"),
    ],
)
def test_pa_action_for_status(status, expected):
    assert pa_action_for_status(status) == expected


def test_format_pa_id_drops_decimal_tail():
    assert _format_pa_id(Decimal("1001.00")) == "1001"


def test_format_pa_id_of_none_is_blank():
    assert _format_pa_id(None) == ""


@pytest.mark.parametrize("raw", ["1001", " 1001 "])
def test_parse_pa_id_accepts_digits(raw):
    assert _parse_pa_id(raw) == Decimal(1001)


@pytest.mark.parametrize("raw", ["abc", "", None])
def test_parse_pa_id_rejects_non_numeric(raw):
    assert _parse_pa_id(raw) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("01,02", {"01", "02"}),
        (" 01 , 02 ", {"01", "02"}),
        ("01,,", {"01"}),
        (None, set()),
        ("", set()),
    ],
)
def test_person_codes(raw, expected):
    assert _person_codes(raw) == expected


def test_drug_name_prefers_catalogue():
    assert _drug_name(make_pa(), make_drug()) == "HUMIRA SOLN 40MG"


def test_drug_name_falls_back_to_manual_then_generic():
    assert _drug_name(make_pa(manualgenname="TYPED IN"), None) == "TYPED IN"
    assert _drug_name(make_pa(manualgenname=None), None) == "ADALIMUMAB"


def test_provider_prefers_prescriber_then_authby():
    assert _provider(make_pa(), make_prescriber()) == "DR. ANITA PATEL"
    assert _provider(make_pa(authby="CLINICAL REVIEW"), None) == "CLINICAL REVIEW"


def test_to_int_handles_none():
    assert _to_int(Decimal(13)) == 13
    assert _to_int(None) is None


def test_audit_user_truncates_to_column_width():
    assert (
        _audit_user("a-very-long-email-address@example.com") == "a-very-long-email-ad"
    )
    assert len(_audit_user("a-very-long-email-address@example.com")) == 20
    assert _audit_user(None) is None


def test_stamp_change_records_actor_and_timestamp():
    pa = make_pa()
    _stamp_change(pa, "tester@example.com")
    assert pa.changeuser == "tester@example.com"[:20]
    assert isinstance(pa.changets, datetime)


class TestReferences:
    def test_member_for_matches_person_code(self):
        first = make_member("MBR001", person_code="01")
        second = make_member("MBR002", person_code="02")
        refs = _References([first, second], [], [])

        assert refs.member_for(make_pa(personcodes="02")) is second

    def test_member_for_family_pa_picks_lowest_code(self):
        first = make_member("MBR001", person_code="01")
        second = make_member("MBR002", person_code="02")
        refs = _References([second, first], [], [])

        assert refs.member_for(make_pa(personcodes="01,02")) is first

    def test_member_for_blank_person_codes_picks_lowest(self):
        first = make_member("MBR001", person_code="01")
        second = make_member("MBR002", person_code="02")
        refs = _References([second, first], [], [])

        assert refs.member_for(make_pa(personcodes=None)) is first

    def test_member_for_returns_none_without_subscribernum(self):
        refs = _References([make_member()], [], [])
        assert refs.member_for(make_pa(subscribernum=None)) is None

    def test_member_for_returns_none_for_unseeded_insured_id(self):
        refs = _References([make_member()], [], [])
        assert refs.member_for(make_pa(subscribernum="INS999")) is None

    def test_member_for_returns_none_when_no_code_matches(self):
        refs = _References([make_member(person_code="01")], [], [])
        assert refs.member_for(make_pa(personcodes="09")) is None

    def test_member_without_insured_id_is_not_indexed(self):
        refs = _References([make_member(insured_id=None)], [], [])
        assert refs.member_for(make_pa()) is None

    def test_drug_and_prescriber_lookups(self):
        refs = _References([], [make_drug()], [make_prescriber()])

        assert refs.drug_for(make_pa()).drug_name == "HUMIRA SOLN 40MG"
        assert refs.drug_for(make_pa(ndc=None)) is None
        assert refs.drug_for(make_pa(ndc="00000000000")) is None
        assert refs.prescriber_for(make_pa()).npi == "1326367012"
        assert refs.prescriber_for(make_pa(prescriberid=None)) is None

    def test_empty_resolves_everything_to_none(self):
        refs = _References.empty()

        assert refs.member_for(make_pa()) is None
        assert refs.drug_for(make_pa()) is None
        assert refs.prescriber_for(make_pa()) is None


def test_to_search_result_maps_member_and_drug():
    refs = _References([make_member()], [make_drug()], [make_prescriber()])
    result = _to_search_result(make_pa(), refs, TODAY)

    assert result.pa_id == "1001"
    assert result.member_id == "MBR001"
    assert result.first_name == "Carlos"
    assert result.last_name == "Martinez"
    assert result.drug_name == "HUMIRA SOLN 40MG"
    assert result.provider == "DR. ANITA PATEL"
    assert result.status is PAStatus.AUTHORIZED


def test_to_search_result_tolerates_unresolved_references():
    result = _to_search_result(make_pa(), _References.empty(), TODAY)

    assert result.member_id is None
    assert result.first_name is None
    assert result.drug_name == "ADALIMUMAB"


def test_to_detail_maps_legacy_columns():
    pa = make_pa(
        deaclass="CII",
        refills="11",
        maxdailydose="0.06",
        maxscriptqty="2",
        maxscriptdays="28",
        source="WEB",
        calledinby="RHEUM CLINIC",
        appeal="N",
        reqreceived=date(2026, 1, 1),
        documentation=date(2026, 1, 2),
        reqapproved=date(2026, 1, 3),
        memnotified=date(2026, 1, 4),
        seconddiagnosis="Z00.00",
        diagnosis="M06.9",
        createuser="admin",
        createts=datetime(2026, 1, 3, 9, 0, 0),
        changeuser="admin",
        changets=datetime(2026, 1, 5, 9, 0, 0),
    )
    detail = _to_detail(pa, _References.empty(), TODAY)

    assert detail.gpi == "66000015100315"
    assert detail.group_number == "GRP001"
    assert detail.person_codes == "01"
    assert detail.prescriber_npi == "1326367012"
    assert detail.pharmacy_nabp == "2400214"
    assert detail.brand_generic == "B"
    assert detail.dea_class == "CII"
    assert detail.max_scripts == 13
    assert detail.days_old == 3
    assert detail.request_approved == date(2026, 1, 3)
    assert detail.created_by == "admin"
    assert detail.changed_at == datetime(2026, 1, 5, 9, 0, 0)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (PAStatus.PENDING, PAStatus.AUTHORIZED),
        (PAStatus.PENDING, PAStatus.DECLINED),
        (PAStatus.PENDING, PAStatus.EXPIRED),
        (PAStatus.AUTHORIZED, PAStatus.DECLINED),
        (PAStatus.AUTHORIZED, PAStatus.EXPIRED),
        (PAStatus.DECLINED, PAStatus.AUTHORIZED),
        (PAStatus.EXPIRED, PAStatus.EXPIRED),
    ],
)
def test_require_valid_transition_allows(current, target):
    _require_valid_transition(current, target, "1001")


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (PAStatus.AUTHORIZED, PAStatus.PENDING),
        (PAStatus.DECLINED, PAStatus.PENDING),
        (PAStatus.DECLINED, PAStatus.EXPIRED),
        (PAStatus.EXPIRED, PAStatus.AUTHORIZED),
        (PAStatus.EXPIRED, PAStatus.PENDING),
    ],
)
def test_require_valid_transition_rejects(current, target):
    with pytest.raises(InvalidStatusTransitionException) as exc:
        _require_valid_transition(current, target, "1001")

    assert exc.value.status_code == 422
    assert "1001" in str(exc.value)


def test_expire_on_or_before_keeps_past_term_date():
    assert _expire_on_or_before(date(2020, 5, 1), TODAY) == date(2020, 5, 1)


def test_expire_on_or_before_pulls_future_back_to_yesterday():
    assert _expire_on_or_before(date(2030, 1, 1), TODAY) == date(2026, 8, 9)
    assert _expire_on_or_before(None, TODAY) == date(2026, 8, 9)


def test_expire_on_or_before_defaults_to_today():
    assert _expire_on_or_before(date(2030, 1, 1)) == date.today() - timedelta(days=1)


def test_apply_status_authorized_sets_approval_and_clears_denial():
    pa = make_pa(action=None, denial="03", reqapproved=None)
    _apply_status(pa, PAStatus.AUTHORIZED, TODAY)

    assert pa.action == "A"
    assert pa.denial is None
    assert pa.reqapproved == TODAY


def test_apply_status_authorized_keeps_existing_approval_date():
    pa = make_pa(reqapproved=date(2026, 1, 3))
    _apply_status(pa, PAStatus.AUTHORIZED, TODAY)

    assert pa.reqapproved == date(2026, 1, 3)


def test_apply_status_declined_clears_approval():
    pa = make_pa(reqapproved=date(2026, 1, 3))
    _apply_status(pa, PAStatus.DECLINED, TODAY)

    assert pa.action == "D"
    assert pa.reqapproved is None


def test_apply_status_pending_clears_action_and_approval():
    pa = make_pa(reqapproved=date(2026, 1, 3), denial="03")
    _apply_status(pa, PAStatus.PENDING, TODAY)

    assert pa.action is None
    assert pa.denial is None
    assert pa.reqapproved is None


def test_apply_status_expired_pulls_term_date_back():
    pa = make_pa(termdate=date(2030, 1, 1))
    _apply_status(pa, PAStatus.EXPIRED, TODAY)

    assert pa.action == "A"
    assert pa.termdate == date(2026, 8, 9)


async def test_get_prior_auth_returns_detail(service: PriorAuthService):
    service._repo.get_by_authnum.return_value = make_pa()
    service._member_repo.get_by_insured_ids.return_value = [make_member()]
    service._drug_repo.get_by_ndcs.return_value = [make_drug()]
    service._prescriber_repo.get_by_npis.return_value = [make_prescriber()]

    detail = await service.get_prior_auth("1001")

    assert detail.pa_id == "1001"
    assert detail.member_id == "MBR001"
    service._repo.get_by_authnum.assert_awaited_once_with(Decimal(1001))


async def test_get_prior_auth_raises_for_unknown_id(service: PriorAuthService):
    service._repo.get_by_authnum.return_value = None

    with pytest.raises(PriorAuthNotFoundException) as exc:
        await service.get_prior_auth("9999")

    assert exc.value.status_code == 404


async def test_get_prior_auth_raises_for_non_numeric_id(service: PriorAuthService):
    with pytest.raises(PriorAuthNotFoundException):
        await service.get_prior_auth("not-a-number")

    service._repo.get_by_authnum.assert_not_called()


async def test_search_resolves_member_id_to_insured_id(service: PriorAuthService):
    service._member_repo.get_by_member_id.return_value = make_member()
    service._repo.search.return_value = ([make_pa()], 1)
    service._member_repo.get_by_insured_ids.return_value = []
    service._drug_repo.get_by_ndcs.return_value = []
    service._prescriber_repo.get_by_npis.return_value = []

    result = await service.search_prior_auths(
        PASearchRequest(searchRequest=PASearch(memberId="MBR001"))
    )

    assert result.pagination.total == 1
    kwargs = service._repo.search.await_args.kwargs
    assert kwargs["insured_id"] == "INS001"
    assert kwargs["person_code"] == "01"
    assert kwargs["subscriber_num"] is None


async def test_search_falls_back_to_subscriber_num(service: PriorAuthService):
    service._member_repo.get_by_member_id.return_value = None
    service._repo.search.return_value = ([], 0)

    result = await service.search_prior_auths(
        PASearchRequest(searchRequest=PASearch(memberId="INS001"))
    )

    assert result.data == []
    kwargs = service._repo.search.await_args.kwargs
    assert kwargs["subscriber_num"] == "INS001"
    assert kwargs["insured_id"] is None


async def test_search_passes_filters_through(service: PriorAuthService):
    service._repo.search.return_value = ([], 0)

    await service.search_prior_auths(
        PASearchRequest(
            searchRequest=PASearch(
                ndc="00074580302",
                status=PAStatus.AUTHORIZED,
                effDateFrom=date(2026, 1, 1),
                effDateTo=date(2026, 12, 31),
            )
        )
    )

    kwargs = service._repo.search.await_args.kwargs
    assert kwargs["ndc"] == "00074580302"
    assert kwargs["status"] is PAStatus.AUTHORIZED
    assert kwargs["eff_date_from"] == date(2026, 1, 1)
    assert kwargs["eff_date_to"] == date(2026, 12, 31)


async def test_search_for_member_scopes_to_that_member(service: PriorAuthService):
    service._member_repo.get_by_member_id.return_value = make_member(person_code="02")
    service._repo.search.return_value = ([], 0)

    await service.search_prior_auths_for_member(
        "MBR002",
        PASearchRequestByMemberPath(searchRequest=PASearchByMemberPath()),
    )

    kwargs = service._repo.search.await_args.kwargs
    assert kwargs["insured_id"] == "INS001"
    assert kwargs["person_code"] == "02"


async def test_search_for_member_raises_when_member_missing(service: PriorAuthService):
    service._member_repo.get_by_member_id.return_value = None

    with pytest.raises(MemberNotFoundException):
        await service.search_prior_auths_for_member(
            "MBR999",
            PASearchRequestByMemberPath(searchRequest=PASearchByMemberPath()),
        )


async def test_get_prior_auths_for_member(service: PriorAuthService):
    service._member_repo.get_by_member_id.return_value = make_member()
    service._repo.search.return_value = ([make_pa()], 1)
    service._member_repo.get_by_insured_ids.return_value = [make_member()]
    service._drug_repo.get_by_ndcs.return_value = []
    service._prescriber_repo.get_by_npis.return_value = []

    result = await service.get_prior_auths_for_member(
        "MBR001", PAByEntityQuery(status=PAStatus.AUTHORIZED)
    )

    assert result.pagination.total == 1
    kwargs = service._repo.search.await_args.kwargs
    assert kwargs["status"] is PAStatus.AUTHORIZED
    assert kwargs["sort_dir"] == "desc"


async def test_get_prior_auths_for_member_raises_when_missing(
    service: PriorAuthService,
):
    service._member_repo.get_by_member_id.return_value = None

    with pytest.raises(MemberNotFoundException) as exc:
        await service.get_prior_auths_for_member("MBR999", PAByEntityQuery())

    assert exc.value.status_code == 404


async def test_get_prior_auths_for_drug(service: PriorAuthService):
    service._drug_repo.get_by_ndc.return_value = make_drug()
    service._repo.search.return_value = ([], 0)

    await service.get_prior_auths_for_drug("00074580302", PAByEntityQuery())

    assert service._repo.search.await_args.kwargs["ndc"] == "00074580302"


async def test_get_prior_auths_for_drug_raises_when_missing(service: PriorAuthService):
    service._drug_repo.get_by_ndc.return_value = None

    with pytest.raises(DrugNotFoundException):
        await service.get_prior_auths_for_drug("00000000000", PAByEntityQuery())


async def test_get_prior_auths_for_prescriber(service: PriorAuthService):
    service._prescriber_repo.get_by_npi.return_value = make_prescriber()
    service._repo.search.return_value = ([], 0)

    await service.get_prior_auths_for_prescriber("1326367012", PAByEntityQuery())

    assert service._repo.search.await_args.kwargs["prescriber_npi"] == "1326367012"


async def test_get_prior_auths_for_prescriber_raises_when_missing(
    service: PriorAuthService,
):
    service._prescriber_repo.get_by_npi.return_value = None

    with pytest.raises(PrescriberNotFoundException):
        await service.get_prior_auths_for_prescriber("0000000000", PAByEntityQuery())


def create_request(**overrides) -> CreatePARequest:
    payload = {
        "memberId": "MBR001",
        "effDate": date(2026, 9, 1),
        "termDate": date(2027, 8, 31),
        "drugName": "HUMIRA",
        "ndc": "00074580302",
        "status": PAStatus.AUTHORIZED,
        "reasonCode": "SPECIALTY",
        "notes": "new pa",
        "diagnosis": "M06.9",
    }
    payload.update(overrides)
    return CreatePARequest(**payload)


async def test_create_allocates_authnum_and_maps_member(service: PriorAuthService):
    plan = PlanModel(plan_id="PLN001", carrier="BCBS", group_number="GRP001")
    service._member_repo.get_by_member_id.return_value = make_member(plan=plan)
    service._drug_repo.get_by_ndc.return_value = make_drug()
    service._repo.next_authnum.return_value = Decimal(1021)
    service._member_repo.get_by_insured_ids.return_value = []
    service._drug_repo.get_by_ndcs.return_value = []
    service._prescriber_repo.get_by_npis.return_value = []

    await service.create_prior_auth(create_request(), actor="tester@example.com")

    added = service._repo.add.await_args.args[0]
    assert added.authnum == Decimal(1021)
    assert added.subscribernum == "INS001"
    assert added.groupnum == "GRP001"
    assert added.personcodes == "01"
    assert added.action == "A"
    assert added.gpi == "66000015100315"
    assert added.manualgenname == "HUMIRA"
    assert added.source == "WEB"
    assert added.createuser == "tester@example.com"[:20]
    assert added.reqapproved == date.today()
    service._session.commit.assert_awaited_once()


async def test_create_without_plan_leaves_group_null(service: PriorAuthService):
    service._member_repo.get_by_member_id.return_value = make_member(plan=None)
    service._drug_repo.get_by_ndc.return_value = make_drug()
    service._repo.next_authnum.return_value = Decimal(1)
    service._member_repo.get_by_insured_ids.return_value = []
    service._drug_repo.get_by_ndcs.return_value = []
    service._prescriber_repo.get_by_npis.return_value = []

    await service.create_prior_auth(create_request())

    assert service._repo.add.await_args.args[0].groupnum is None


async def test_create_pending_leaves_action_and_approval_unset(
    service: PriorAuthService,
):
    service._member_repo.get_by_member_id.return_value = make_member()
    service._drug_repo.get_by_ndc.return_value = make_drug()
    service._repo.next_authnum.return_value = Decimal(1)
    service._member_repo.get_by_insured_ids.return_value = []
    service._drug_repo.get_by_ndcs.return_value = []
    service._prescriber_repo.get_by_npis.return_value = []

    await service.create_prior_auth(create_request(status=PAStatus.PENDING))

    added = service._repo.add.await_args.args[0]
    assert added.action is None
    assert added.reqapproved is None


async def test_create_expired_pulls_term_date_back(service: PriorAuthService):
    service._member_repo.get_by_member_id.return_value = make_member()
    service._drug_repo.get_by_ndc.return_value = make_drug()
    service._repo.next_authnum.return_value = Decimal(1)
    service._member_repo.get_by_insured_ids.return_value = []
    service._drug_repo.get_by_ndcs.return_value = []
    service._prescriber_repo.get_by_npis.return_value = []

    await service.create_prior_auth(create_request(status=PAStatus.EXPIRED))

    assert service._repo.add.await_args.args[0].termdate < date.today()


async def test_create_uses_supplied_gpi(service: PriorAuthService):
    service._member_repo.get_by_member_id.return_value = make_member()
    service._drug_repo.get_by_ndc.return_value = make_drug()
    service._repo.next_authnum.return_value = Decimal(1)
    service._member_repo.get_by_insured_ids.return_value = []
    service._drug_repo.get_by_ndcs.return_value = []
    service._prescriber_repo.get_by_npis.return_value = []

    await service.create_prior_auth(create_request(gpi="27600030010320"))

    assert service._repo.add.await_args.args[0].gpi == "27600030010320"


async def test_create_raises_422_for_unknown_member(service: PriorAuthService):
    service._member_repo.get_by_member_id.return_value = None

    with pytest.raises(MemberNotFoundException) as exc:
        await service.create_prior_auth(create_request(memberId="MBR999"))

    assert exc.value.status_code == 422


async def test_create_raises_for_unknown_ndc(service: PriorAuthService):
    service._member_repo.get_by_member_id.return_value = make_member()
    service._drug_repo.get_by_ndc.return_value = None

    with pytest.raises(DrugNotFoundException):
        await service.create_prior_auth(create_request())


def update_request(**overrides) -> UpdatePARequest:
    payload = {
        "effDate": date(2026, 9, 1),
        "termDate": date(2027, 8, 31),
        "drugName": "HUMIRA",
        "ndc": "00074580302",
        "status": PAStatus.AUTHORIZED,
        "reasonCode": "SPECIALTY",
        "notes": "updated",
        "diagnosis": "M06.9",
    }
    payload.update(overrides)
    return UpdatePARequest(**payload)


async def test_update_replaces_fields(service: PriorAuthService):
    pa = make_pa()
    service._repo.get_by_authnum.return_value = pa
    service._member_repo.get_by_insured_ids.return_value = []
    service._drug_repo.get_by_ndcs.return_value = []
    service._prescriber_repo.get_by_npis.return_value = []

    await service.update_prior_auth("1001", update_request(), actor="tester")

    assert pa.effdate == date(2026, 9, 1)
    assert pa.termdate == date(2027, 8, 31)
    assert pa.manualgenname == "HUMIRA"
    assert pa.notes == "updated"
    assert pa.changeuser == "tester"
    service._session.commit.assert_awaited_once()


async def test_update_rejects_expired_pa(service: PriorAuthService):
    service._repo.get_by_authnum.return_value = make_pa(termdate=date(2020, 1, 1))

    with pytest.raises(PriorAuthNotEditableException) as exc:
        await service.update_prior_auth("1001", update_request())

    assert exc.value.status_code == 403


async def test_update_rejects_invalid_transition(service: PriorAuthService):
    service._repo.get_by_authnum.return_value = make_pa()

    with pytest.raises(InvalidStatusTransitionException):
        await service.update_prior_auth("1001", update_request(status=PAStatus.PENDING))


async def test_update_to_expired_pulls_term_date_back(service: PriorAuthService):
    pa = make_pa()
    service._repo.get_by_authnum.return_value = pa
    service._member_repo.get_by_insured_ids.return_value = []
    service._drug_repo.get_by_ndcs.return_value = []
    service._prescriber_repo.get_by_npis.return_value = []

    await service.update_prior_auth("1001", update_request(status=PAStatus.EXPIRED))

    assert pa.termdate < date.today()


async def test_patch_updates_only_supplied_fields(service: PriorAuthService):
    pa = make_pa(notes="original", reasoncode="SPECIALTY")
    service._repo.get_by_authnum.return_value = pa
    service._member_repo.get_by_insured_ids.return_value = []
    service._drug_repo.get_by_ndcs.return_value = []
    service._prescriber_repo.get_by_npis.return_value = []

    await service.patch_prior_auth("1001", PatchPARequest(notes="patched"))

    assert pa.notes == "patched"
    assert pa.reasoncode == "SPECIALTY"
    assert pa.action == "A"


async def test_patch_applies_status_transition(service: PriorAuthService):
    pa = make_pa(action=None, reqapproved=None)
    service._repo.get_by_authnum.return_value = pa
    service._member_repo.get_by_insured_ids.return_value = []
    service._drug_repo.get_by_ndcs.return_value = []
    service._prescriber_repo.get_by_npis.return_value = []

    await service.patch_prior_auth("1001", PatchPARequest(status=PAStatus.DECLINED))

    assert pa.action == "D"


async def test_patch_rejects_invalid_transition(service: PriorAuthService):
    service._repo.get_by_authnum.return_value = make_pa()

    with pytest.raises(InvalidStatusTransitionException):
        await service.patch_prior_auth("1001", PatchPARequest(status=PAStatus.PENDING))


async def test_patch_rejects_expired_pa(service: PriorAuthService):
    service._repo.get_by_authnum.return_value = make_pa(termdate=date(2020, 1, 1))

    with pytest.raises(PriorAuthNotEditableException):
        await service.patch_prior_auth("1001", PatchPARequest(notes="x"))


async def test_patch_clears_reason_code_when_explicitly_null(
    service: PriorAuthService,
):
    pa = make_pa(reasoncode="SPECIALTY")
    service._repo.get_by_authnum.return_value = pa
    service._member_repo.get_by_insured_ids.return_value = []
    service._drug_repo.get_by_ndcs.return_value = []
    service._prescriber_repo.get_by_npis.return_value = []

    await service.patch_prior_auth("1001", PatchPARequest(reasonCode=None))

    assert pa.reasoncode is None


async def test_load_references_batches_by_unique_keys(service: PriorAuthService):
    service._member_repo.get_by_insured_ids.return_value = []
    service._drug_repo.get_by_ndcs.return_value = []
    service._prescriber_repo.get_by_npis.return_value = []

    await service._load_references(
        [make_pa(), make_pa(authnum=Decimal(1002)), make_pa(authnum=Decimal(1003))]
    )

    assert service._member_repo.get_by_insured_ids.await_args.args[0] == ["INS001"]
    assert service._drug_repo.get_by_ndcs.await_args.args[0] == ["00074580302"]
    assert service._prescriber_repo.get_by_npis.await_args.args[0] == ["1326367012"]


async def test_load_references_skips_queries_when_page_empty(
    service: PriorAuthService,
):
    refs = await service._load_references([])

    assert refs.member_for(make_pa()) is None
    service._member_repo.get_by_insured_ids.assert_not_called()
