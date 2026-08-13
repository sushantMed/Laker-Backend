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
    PASearchByMemberPath,
    PASearchRequest,
    PASearchRequestByMemberPath,
    PASearchResult,
    PatchPARequest,
    UpdatePARequest,
)
from app.utils.enums import PAStatus


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


def test_member_path_search_allows_no_criteria():
    criteria = PASearchByMemberPath()

    assert criteria.pa_id is None
    assert criteria.status is None


def test_member_path_search_validates_date_range():
    with pytest.raises(InvalidDateRangeException):
        PASearchByMemberPath(effDateFrom=date(2026, 5, 1), effDateTo=date(2026, 4, 1))


def test_member_path_search_strips_blanks():
    assert PASearchByMemberPath(drugName="  ").drug_name is None


def test_member_path_request_envelope():
    request = PASearchRequestByMemberPath(searchRequest=PASearchByMemberPath())

    assert request.pagination.page == 1


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
