from __future__ import annotations

import pytest

from app.core.exceptions import MissingSearchCriteriaException
from app.schemas.drug_schema import DrugSearch
from app.schemas.pharmacy_schema import PharmacySearch
from app.schemas.prescriber_schema import PrescriberSearch
from app.utils.enums import BrandGeneric, Maintenance


def test_drug_search_accepts_single_criterion():
    search = DrugSearch(name="Atorvastatin")
    assert search.name == "Atorvastatin"


def test_drug_search_accepts_enum_criteria():
    search = DrugSearch(brandGeneric="GENERIC", maintenance="YES")
    assert search.brand_generic == BrandGeneric.GENERIC
    assert search.maintenance == Maintenance.YES


def test_drug_search_requires_at_least_one_criterion():
    with pytest.raises(MissingSearchCriteriaException):
        DrugSearch()


@pytest.mark.parametrize("tier", [0, 6])
def test_drug_search_rejects_out_of_range_tier(tier):
    with pytest.raises(Exception):
        DrugSearch(tier=tier)


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
