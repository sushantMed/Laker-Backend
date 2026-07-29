import pytest  # type: ignore

from app.core.rbac import (
    ALL_PERMISSIONS,
    PERNAME_RESOURCES,
    Perm,
    grant_map,
    group_permissions,
    permissions_from_grants,
    resource_for_pername,
    response_key,
    validate_permission_catalog,
)


def test_catalog_covers_every_perm_constant():
    validate_permission_catalog()  # raises if a Perm code has no pername source


def test_view_grant_expands_to_view_and_search():
    perms = permissions_from_grants([("Memeber Screen", "Y", "N")])
    assert perms == {
        Perm.MEMBER_VIEW,
        Perm.MEMBER_SEARCH,
        Perm.MEMBER_SEARCH_PREVCARDID,
    }
    assert Perm.MEMBER_SAVE not in perms


def test_save_grant_adds_save():
    perms = permissions_from_grants([("Memeber Screen", "Y", "Y")])
    assert Perm.MEMBER_SAVE in perms


def test_save_without_view_grants_only_save():
    assert permissions_from_grants([("Memeber Screen", "N", "Y")]) == {Perm.MEMBER_SAVE}


@pytest.mark.parametrize("flag", ["N", "n", 0, "0", None, "", False, "junk"])
def test_falsy_flags_grant_nothing(flag):
    assert permissions_from_grants([("Memeber Screen", flag, flag)]) == set()


@pytest.mark.parametrize("flag", ["Y", "y", 1, "1", True])
def test_truthy_flag_variants(flag):
    """'Y'/'N' is what we store; the numeric forms are tolerated for rows
    imported from the legacy NUMBER(1) columns."""
    assert Perm.MEMBER_VIEW in permissions_from_grants([("Memeber Screen", flag, "N")])


@pytest.mark.parametrize(
    "pername", ["Memeber Screen", "memeber screen", "  MEMEBER   SCREEN  "]
)
def test_pername_lookup_is_case_and_whitespace_insensitive(pername):
    assert resource_for_pername(pername) == "member"


def test_unknown_pername_is_skipped_not_raised():
    perms = permissions_from_grants(
        [("some brand new screen", "Y", "Y"), ("Paid claim lookup screen", "Y", "N")]
    )
    assert perms == {Perm.CLAIM_VIEW}


def test_no_grants_fails_closed():
    assert permissions_from_grants([]) == set()


def test_legacy_screens_are_all_mapped():
    legacy = [
        "Memeber Screen",
        "Mem cancel Card Request",
        "Paid claim lookup screen",
        "membercob",
        "member prior auth",
        "mem subgroups",
        "memdenynotes",
        "mem term date limit",
        "tran lookup screen",
        "subs prescriber restrict",
        "web member dependents",
        "pricing",
        "web accum",
    ]
    assert all(resource_for_pername(p) is not None for p in legacy)
    granted = permissions_from_grants([(p, "Y", "Y") for p in legacy])
    assert granted <= ALL_PERMISSIONS
    assert len(granted) == 2 * len(legacy) + 2  # view+save each, +2 implied searches


def test_grant_map_is_keyed_by_hyphenated_pername():
    assert grant_map(
        [("Memeber Screen", "Y", "Y"), ("pricing", "Y", "N"), ("web accum", "N", "Y")]
    ) == {
        "Memeber-Screen": ["save", "view"],
        "pricing": ["view"],
        "web-accum": ["save"],
    }


def test_grant_map_omits_screens_with_no_flag_set():
    assert grant_map([("pricing", "N", "N")]) == {}


def test_grant_map_keeps_pername_wording_including_unmapped():
    """The map is the user's grant data, not the subset we enforce — only the
    spaces change, so the client still recognizes the screen."""
    assert grant_map([("some brand new screen", "Y", "N")]) == {
        "some-brand-new-screen": ["view"]
    }


def test_grant_map_merges_duplicate_rows():
    assert grant_map([("pricing", "Y", "N"), ("pricing", "N", "Y")]) == {
        "pricing": ["save", "view"]
    }


def test_grant_map_preserves_case_and_collapses_whitespace_runs():
    """Only whitespace is touched: casing survives, and a run of it yields one
    '-' rather than several."""
    assert grant_map([("  MEMEBER   SCREEN  ", "Y", "N")]) == {
        "MEMEBER-SCREEN": ["view"]
    }


def test_grant_map_unions_rows_that_collide_once_hyphenated():
    """A row already spelled with a hyphen lands on the same key as its spaced
    twin — flags merge, neither row is dropped."""
    assert grant_map([("mem subgroups", "Y", "N"), ("mem-subgroups", "N", "Y")]) == {
        "mem-subgroups": ["save", "view"]
    }


def test_response_key_does_not_feed_authorization():
    """The hyphenated key is presentation only: it must not resolve back to a
    resource, which is why authorization reads the stored pername instead."""
    assert resource_for_pername("Memeber Screen") == "member"
    assert resource_for_pername(response_key("Memeber Screen")) is None


@pytest.mark.parametrize("pername", list(PERNAME_RESOURCES))
def test_hyphenating_keeps_every_screen_distinct(pername):
    """No two screens may collapse onto one key — that would let the client
    conflate grants on different screens."""
    keys = [response_key(p) for p in PERNAME_RESOURCES]
    assert len(set(keys)) == len(keys)
    assert " " not in response_key(pername)


def test_group_permissions_shape():
    assert group_permissions({"member:view", "member:save", "claim:view"}) == {
        "claim": ["view"],
        "member": ["save", "view"],
    }
