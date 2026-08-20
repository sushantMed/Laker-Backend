from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from app.core.exceptions import InvalidDateRangeException, NoSearchCriteriaException
from app.schemas.prior_auth_schema import (
    CreatePARequest,
    PAByEntityQuery,
    PADetail,
    PASearch,
    PASearchBySubscriber,
    PASearchRequest,
    PASearchRequestBySubscriber,
    PASearchResult,
    PatchPARequest,
    UpdatePARequest,
)
from app.utils.enums import PAStatus


def subscriber_criteria(**criteria) -> PASearchBySubscriber:
    """The search criteria, with the two required cardholder keys filled in."""
    criteria.setdefault("subscriberNum", "INS001")
    criteria.setdefault("personCodes", "01")
    return PASearchBySubscriber(**criteria)


def test_search_accepts_a_single_criterion():
    criteria = PASearch(ndc="00074580302")

    assert criteria.ndc == "00074580302"
    assert criteria.pa_id is None


def test_search_rejects_empty_criteria():
    with pytest.raises(NoSearchCriteriaException):
        PASearch()


def test_search_treats_blank_strings_as_absent():
    with pytest.raises(NoSearchCriteriaException):
        PASearch(paId="   ", memberId="", drugName=" ", ndc="")


def test_search_strips_whitespace():
    criteria = PASearch(memberId="  MBR001  ")

    assert criteria.member_id == "MBR001"


def test_search_accepts_status_only():
    assert PASearch(status=PAStatus.PENDING).status is PAStatus.PENDING


def test_search_accepts_date_only():
    assert PASearch(effDateFrom=date(2026, 1, 1)).eff_date_from == date(2026, 1, 1)


def test_search_rejects_reversed_date_range():
    with pytest.raises(InvalidDateRangeException):
        PASearch(effDateFrom=date(2026, 12, 31), effDateTo=date(2026, 1, 1))


def test_search_allows_equal_dates():
    criteria = PASearch(effDateFrom=date(2026, 1, 1), effDateTo=date(2026, 1, 1))

    assert criteria.eff_date_to == date(2026, 1, 1)


def test_search_request_defaults_sort_and_pagination():
    request = PASearchRequest(searchRequest=PASearch(ndc="00074580302"))

    assert request.pagination.page == 1
    assert request.pagination.page_size == 20
    assert request.sort.sort_dir == "ASC"


@pytest.mark.parametrize(
    "missing", [{"personCodes": "01"}, {"subscriberNum": "INS001"}, {}]
)
def test_subscriber_search_requires_the_cardholder_keys(missing):
    """subscriberNum and personCodes identify the cardholder -- both are required."""
    with pytest.raises(ValidationError):
        PASearchBySubscriber(**missing)


@pytest.mark.parametrize("blank", ["", "   "])
def test_subscriber_search_rejects_blank_cardholder_keys(blank):
    with pytest.raises(ValidationError):
        PASearchBySubscriber(subscriberNum=blank, personCodes="01")
    with pytest.raises(ValidationError):
        PASearchBySubscriber(subscriberNum="INS001", personCodes=blank)


def test_subscriber_search_strips_the_cardholder_keys():
    criteria = PASearchBySubscriber(subscriberNum="  INS001  ", personCodes=" 01 ")

    assert criteria.subscriber_num == "INS001"
    assert criteria.person_codes == "01"


def test_subscriber_search_rejects_a_person_code_wider_than_the_column():
    """SUBSCRIBER.PERSONCODE is 2 wide, so a comma list is not a person code."""
    with pytest.raises(ValidationError):
        PASearchBySubscriber(subscriberNum="INS001", personCodes="01,02")


def test_subscriber_search_allows_no_criteria():
    criteria = subscriber_criteria()

    assert criteria.ndc is None
    assert criteria.eff_date is None
    assert criteria.term_date is None
    assert criteria.eff_date_from is None
    assert criteria.eff_date_to is None


def test_subscriber_search_parses_eff_date_bounds():
    criteria = subscriber_criteria(effDateFrom="05/01/2025", effDateTo="04/30/2026")

    assert criteria.eff_date_from == date(2025, 5, 1)
    assert criteria.eff_date_to == date(2026, 4, 30)


def test_subscriber_search_accepts_one_eff_date_bound_alone():
    assert subscriber_criteria(effDateFrom="05/01/2025").eff_date_to is None
    assert subscriber_criteria(effDateTo="04/30/2026").eff_date_from is None


def test_subscriber_search_allows_an_eff_date_range_of_one_day():
    criteria = subscriber_criteria(effDateFrom="05/01/2025", effDateTo="05/01/2025")

    assert criteria.eff_date_from == criteria.eff_date_to


def test_subscriber_search_rejects_reversed_eff_date_range():
    with pytest.raises(InvalidDateRangeException):
        subscriber_criteria(effDateFrom="04/30/2026", effDateTo="05/01/2025")


@pytest.mark.parametrize("blank", ["", "   ", None])
def test_subscriber_search_treats_blank_eff_date_bounds_as_absent(blank):
    criteria = subscriber_criteria(effDateFrom=blank, effDateTo=blank)

    assert criteria.eff_date_from is None
    assert criteria.eff_date_to is None


def test_subscriber_search_parses_eff_and_term_dates():
    criteria = subscriber_criteria(effDate="05/01/2025", termDate="04/30/2026")

    assert criteria.eff_date == date(2025, 5, 1)
    assert criteria.term_date == date(2026, 4, 30)


def test_subscriber_search_strips_blanks():
    assert subscriber_criteria(ndc="  ").ndc is None


@pytest.mark.parametrize(
    ("keyed", "expected"),
    [
        ("093721410", "00093721410"),
        ("0093721410", "00093721410"),
        ("00093721410", "00093721410"),
        ("  093721410  ", "00093721410"),
    ],
)
def test_subscriber_search_pads_short_ndc(keyed, expected):
    """A 9- or 10-char NDC is zero-padded to the stored 11-char width."""
    assert subscriber_criteria(ndc=keyed).ndc == expected


@pytest.mark.parametrize("keyed", ["9372141", "93721410", "000937214100"])
def test_subscriber_search_rejects_out_of_range_ndc(keyed):
    """Under 9 or over 11 characters is a bad NDC, not something to pad."""
    with pytest.raises(ValidationError):
        subscriber_criteria(ndc=keyed)


@pytest.mark.parametrize("blank", ["", "   ", None])
def test_subscriber_search_treats_blank_dates_as_absent(blank):
    criteria = subscriber_criteria(effDate=blank, termDate=blank)

    assert criteria.eff_date is None
    assert criteria.term_date is None


def test_subscriber_search_still_rejects_malformed_dates():
    with pytest.raises(ValidationError):
        subscriber_criteria(effDate="13/45/2025")


@pytest.mark.parametrize(
    "field", ["memberId", "paId", "drugName", "provider", "status"]
)
def test_subscriber_search_ignores_unsupported_criteria(field):
    """Only the known keys survive; anything else is accepted and dropped."""
    criteria = subscriber_criteria(**{field: "x"}, ndc="00088502005")

    assert criteria.ndc == "00088502005"
    assert set(criteria.model_dump()) == {
        "subscriber_num",
        "person_codes",
        "ndc",
        "eff_date",
        "eff_date_from",
        "eff_date_to",
        "term_date",
    }


def test_subscriber_request_envelope():
    request = PASearchRequestBySubscriber(searchRequest=subscriber_criteria())

    assert request.pagination.page == 1
    assert request.pagination.page_size == 20


@pytest.mark.parametrize("page_size", [10, 25, 50, 100, 10_000])
def test_subscriber_request_allows_large_page_sizes(page_size):
    request = PASearchRequestBySubscriber(
        searchRequest=subscriber_criteria(),
        pagination={"page": 1, "pageSize": page_size},
    )

    assert request.pagination.page_size == page_size


def test_subscriber_request_rejects_page_size_above_cap():
    with pytest.raises(ValidationError):
        PASearchRequestBySubscriber(
            searchRequest=subscriber_criteria(),
            pagination={"page": 1, "pageSize": 10_001},
        )


def test_by_entity_query_defaults():
    query = PAByEntityQuery()

    assert query.page == 1
    assert query.page_size == 20
    assert query.status is None


def test_by_entity_query_accepts_camel_case_page_size():
    assert PAByEntityQuery(pageSize=50).page_size == 50


def create_payload(**overrides) -> dict:
    payload = {
        "memberId": "MBR001",
        "effDate": date(2026, 9, 1),
        "termDate": date(2027, 8, 31),
        "drugName": "HUMIRA",
        "ndc": "00074580302",
        "status": PAStatus.AUTHORIZED,
    }
    payload.update(overrides)
    return payload


def test_create_request_maps_camel_case_aliases():
    request = CreatePARequest(**create_payload(gpi="66000015100315"))

    assert request.member_id == "MBR001"
    assert request.eff_date == date(2026, 9, 1)
    assert request.term_date == date(2027, 8, 31)
    assert request.drug_name == "HUMIRA"
    assert request.gpi == "66000015100315"


def test_create_request_rejects_term_before_eff():
    with pytest.raises(InvalidDateRangeException):
        CreatePARequest(
            **create_payload(effDate=date(2027, 1, 1), termDate=date(2026, 1, 1))
        )


def test_create_request_allows_same_day_term():
    request = CreatePARequest(
        **create_payload(effDate=date(2026, 9, 1), termDate=date(2026, 9, 1))
    )

    assert request.term_date == request.eff_date


@pytest.mark.parametrize("ndc", ["1234567890", "123456789012", "0007458030A", ""])
def test_create_request_rejects_malformed_ndc(ndc):
    with pytest.raises(ValidationError):
        CreatePARequest(**create_payload(ndc=ndc))


@pytest.mark.parametrize("gpi", ["6600001510031", "660000151003155", "66000015-0031"])
def test_create_request_rejects_malformed_gpi(gpi):
    with pytest.raises(ValidationError):
        CreatePARequest(**create_payload(gpi=gpi))


def test_create_request_allows_absent_gpi():
    assert CreatePARequest(**create_payload()).gpi is None


def test_create_request_enforces_drug_name_column_width():
    CreatePARequest(**create_payload(drugName="X" * 70))

    with pytest.raises(ValidationError):
        CreatePARequest(**create_payload(drugName="X" * 71))


def test_create_request_enforces_provider_column_width():
    CreatePARequest(**create_payload(provider="X" * 50))

    with pytest.raises(ValidationError):
        CreatePARequest(**create_payload(provider="X" * 51))


def test_create_request_enforces_reason_code_column_width():
    CreatePARequest(**create_payload(reasonCode="X" * 20))

    with pytest.raises(ValidationError):
        CreatePARequest(**create_payload(reasonCode="X" * 21))


def test_create_request_enforces_notes_and_diagnosis_limits():
    CreatePARequest(**create_payload(notes="X" * 2000, diagnosis="X" * 100))

    with pytest.raises(ValidationError):
        CreatePARequest(**create_payload(notes="X" * 2001))

    with pytest.raises(ValidationError):
        CreatePARequest(**create_payload(diagnosis="X" * 101))


def test_create_request_requires_status():
    payload = create_payload()
    del payload["status"]

    with pytest.raises(ValidationError):
        CreatePARequest(**payload)


def test_update_request_has_no_member_id():
    payload = create_payload()
    del payload["memberId"]
    request = UpdatePARequest(**payload)

    assert not hasattr(request, "member_id")


def test_update_request_rejects_term_before_eff():
    payload = create_payload(effDate=date(2027, 1, 1), termDate=date(2026, 1, 1))
    del payload["memberId"]

    with pytest.raises(InvalidDateRangeException):
        UpdatePARequest(**payload)


def test_patch_request_tracks_which_fields_were_supplied():
    request = PatchPARequest(notes="only notes")

    assert request.model_fields_set == {"notes"}
    assert request.status is None


def test_patch_request_records_explicit_nulls():
    request = PatchPARequest(reasonCode=None)

    assert "reason_code" in request.model_fields_set
    assert request.reason_code is None


def test_patch_request_accepts_empty_body():
    assert PatchPARequest().model_fields_set == set()


def test_patch_request_enforces_column_widths():
    with pytest.raises(ValidationError):
        PatchPARequest(reasonCode="X" * 21)

    with pytest.raises(ValidationError):
        PatchPARequest(notes="X" * 2001)


def test_search_result_requires_only_pa_id_and_status():
    result = PASearchResult(paId="1001", status=PAStatus.AUTHORIZED)

    assert result.member_id is None
    assert result.drug_name is None


def test_search_result_serializes_camel_case_and_dates():
    result = PASearchResult(
        paId="1001",
        memberId="MBR001",
        firstName="Carlos",
        lastName="Martinez",
        effDate=date(2026, 1, 1),
        status=PAStatus.AUTHORIZED,
    )
    dumped = result.model_dump(by_alias=True, mode="json")

    assert dumped["paId"] == "1001"
    assert dumped["firstName"] == "Carlos"
    assert dumped["effDate"] == "01/01/2026"


def test_detail_extends_search_result():
    detail = PADetail(
        paId="1001",
        status=PAStatus.DECLINED,
        groupNumber="GRP001",
        prescriberNpi="1326367012",
        maxScripts=13,
        daysOld=3,
    )
    dumped = detail.model_dump(by_alias=True)

    assert dumped["groupNumber"] == "GRP001"
    assert dumped["prescriberNpi"] == "1326367012"
    assert dumped["maxScripts"] == 13
    assert dumped["daysOld"] == 3
