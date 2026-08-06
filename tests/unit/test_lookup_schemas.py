from __future__ import annotations

import pytest

from app.core.exceptions import (
    InvalidSearchCriteriaException,
    MissingSearchCriteriaException,
)
from app.schemas.drug_schema import DrugSearch
from app.schemas.pharmacy_schema import PharmacySearch
from app.schemas.prescriber_schema import PrescriberSearch
from app.utils.enums import BrandGeneric, Maintenance


def test_drug_search_accepts_single_criterion():
    search = DrugSearch(name="Atorvastatin")
    assert search.name == "Atorvastatin"


def test_drug_search_accepts_enum_criteria():
    search = DrugSearch(brandGeneric="Generic Name", maintenance="YES")
    assert search.brand_generic == BrandGeneric.GENERIC
    assert search.maintenance == Maintenance.YES


def test_drug_search_requires_at_least_one_criterion():
    with pytest.raises(MissingSearchCriteriaException):
        DrugSearch()


@pytest.mark.parametrize("ndc", ["12345678", "123456789012"])
def test_drug_search_rejects_out_of_range_ndc_length(ndc):
    with pytest.raises(InvalidSearchCriteriaException):
        DrugSearch(ndc=ndc)


def test_drug_search_pads_nine_digit_ndc():
    assert DrugSearch(ndc="093721410").ndc == "00093721410"


@pytest.mark.parametrize("ndc", ["0093721410", "00093721410"])
def test_drug_search_keeps_longer_ndc_as_is(ndc):
    assert DrugSearch(ndc=ndc).ndc == ndc


def test_pharmacy_search_accepts_single_criterion():
    search = PharmacySearch(city="Springfield")
    assert search.city == "Springfield"


def test_pharmacy_search_requires_at_least_one_criterion():
    with pytest.raises(MissingSearchCriteriaException):
        PharmacySearch()


def test_pharmacy_search_boolean_flags_do_not_count_as_criteria():
    with pytest.raises(MissingSearchCriteriaException):
        PharmacySearch(is24Hour=True, inNetwork=False)


def test_pharmacy_search_rejects_too_long_state():
    with pytest.raises(Exception):
        PharmacySearch(state="ILL")


def test_prescriber_search_accepts_single_criterion():
    search = PrescriberSearch(specialty="Cardiology")
    assert search.specialty == "Cardiology"


def test_prescriber_search_requires_at_least_one_criterion():
    with pytest.raises(MissingSearchCriteriaException):
        PrescriberSearch()


def test_prescriber_search_rejects_too_long_state():
    with pytest.raises(Exception):
        PrescriberSearch(state="ILL")
