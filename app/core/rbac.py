"""Permissions, sourced entirely from the `user_permissions` rows a user holds.

There are no roles: a user can do exactly what their grants say, and nothing is
inferred from who they are. `users.roles` still exists as a column but no longer
feeds authorization.
"""

import re
from collections.abc import Iterable
from typing import Any

VIEWPERM = "viewperm"
SAVEPERM = "saveperm"


class Perm:
    # Ours.
    DRUG_VIEW = "drug:view"
    DRUG_SAVE = "drug:save"
    GROUPS_VIEW = "groups:view"
    GROUPS_SAVE = "groups:save"
    USERADMIN_VIEW = "useradmin:view"
    USERADMIN_SAVE = "useradmin:save"

    # The legacy screens, one view/save pair per `sql.userperm.pername`.
    MEMBER_VIEW = "member:view"
    MEMBER_SAVE = "member:save"
    MEMBER_SEARCH = "member:search"
    MEMBER_SEARCH_PREVCARDID = "member:searchwithprevcardid"
    MEMCARDCANCEL_VIEW = "memcardcancel:view"
    MEMCARDCANCEL_SAVE = "memcardcancel:save"
    CLAIM_VIEW = "claim:view"
    CLAIM_SAVE = "claim:save"
    MEMBERCOB_VIEW = "membercob:view"
    MEMBERCOB_SAVE = "membercob:save"
    MEMBERPRIORAUTH_VIEW = "memberpriorauth:view"
    MEMBERPRIORAUTH_SAVE = "memberpriorauth:save"
    MEMSUBGROUPS_VIEW = "memsubgroups:view"
    MEMSUBGROUPS_SAVE = "memsubgroups:save"
    MEMDENYNOTES_VIEW = "memdenynotes:view"
    MEMDENYNOTES_SAVE = "memdenynotes:save"
    MEMTERMDATELIMIT_VIEW = "memtermdatelimit:view"
    MEMTERMDATELIMIT_SAVE = "memtermdatelimit:save"
    TRAN_VIEW = "tran:view"
    TRAN_SAVE = "tran:save"
    SUBSPRESCRIBERRESTRICT_VIEW = "subsprescriberrestrict:view"
    SUBSPRESCRIBERRESTRICT_SAVE = "subsprescriberrestrict:save"
    MEMBERDEPENDENTS_VIEW = "memberdependents:view"
    MEMBERDEPENDENTS_SAVE = "memberdependents:save"
    PRICING_VIEW = "pricing:view"
    PRICING_SAVE = "pricing:save"
    ACCUM_VIEW = "accum:view"
    ACCUM_SAVE = "accum:save"


ALL_PERMISSIONS: set[str] = {
    v for k, v in vars(Perm).items() if not k.startswith("_") and isinstance(v, str)
}


# Screen name -> resource slug. Keys carry the canonical casing (they seed rows
# and reach clients through /auth/me); lookups go through _NORMALIZED_RESOURCES
# below, so the casing and spacing of an actual row don't matter. "Memeber
# Screen" keeps its typo because that is what the `sql.userperm` rows contain.
#
# Every screen gets its own resource: two pernames sharing one would let a grant
# on either screen open the other.
PERNAME_RESOURCES: dict[str, str] = {
    "Memeber Screen": "member",
    "Mem cancel Card Request": "memcardcancel",
    "Paid claim lookup screen": "claim",
    "membercob": "membercob",
    "member prior auth": "memberpriorauth",
    "mem subgroups": "memsubgroups",
    "memdenynotes": "memdenynotes",
    "mem term date limit": "memtermdatelimit",
    "tran lookup screen": "tran",
    "subs prescriber restrict": "subsprescriberrestrict",
    "web member dependents": "memberdependents",
    "pricing": "pricing",
    "web accum": "accum",
    "drug lookup screen": "drug",
    "groups screen": "groups",
    "user admin": "useradmin",
}

# Permissions a `viewperm` grant carries beyond `<resource>:view` itself. The
# member screen's searches are how the UI reaches the screen, so they ride along
# with view rather than needing a screen of their own.
_IMPLIED_BY_VIEW: dict[str, tuple[str, ...]] = {
    "member": (Perm.MEMBER_SEARCH, Perm.MEMBER_SEARCH_PREVCARDID),
}

# What the legacy CHAR(1) flags count as granted. Rows imported from the older
# NUMBER(1) columns arrive as 1/0, hence the numeric forms; anything else —
# 'N', NULL, empty, junk — fails closed.
_GRANTED_FLAGS = frozenset({"y", "1", "true"})

_WHITESPACE = re.compile(r"\s+")


def _normalize_pername(pername: str) -> str:
    return _WHITESPACE.sub(" ", str(pername)).strip().lower()


def response_key(pername: str) -> str:
    """A pername as /auth/me spells it: internal whitespace joined with '-'.

    Presentation only, for clients that would rather not quote a space-bearing
    key. Words and casing are left alone -- "Memeber Screen" becomes
    "Memeber-Screen", "pricing" stays "pricing" -- and runs of whitespace
    collapse to a single '-' so a sloppy row doesn't yield "mem---subgroups".

    Deliberately not part of authorization: nothing turns a response key back
    into a lookup, so this doesn't have to be reversible. Grants are matched on
    the stored pername via resource_for_pername(), which normalizes spaces
    rather than hyphens -- feeding a key from here back into it would not
    resolve.
    """
    return _WHITESPACE.sub("-", str(pername).strip())


_NORMALIZED_RESOURCES: dict[str, str] = {
    _normalize_pername(pername): resource
    for pername, resource in PERNAME_RESOURCES.items()
}


def _is_granted(flag: Any) -> bool:
    return str(flag).strip().lower() in _GRANTED_FLAGS


def grant_map(grants: Iterable[tuple[str, Any, Any]]) -> dict[str, list[str]]:
    """The user's grants as ``{screen: [granted flag names]}`` — what /auth/me
    returns, and a direct projection of the legacy query's three columns:

        {"Memeber-Screen": ["saveperm", "viewperm"], "pricing": ["viewperm"]}

    Keys are the stored pername run through response_key(), so the screen name
    survives intact apart from its spaces becoming '-'. Screens holding neither
    flag are omitted — a row with both set to 'N' grants nothing, so listing it
    would imply access the user doesn't have. Unmapped screens are kept: this is
    the user's grant data, not the subset we happen to enforce.
    """
    granted: dict[str, list[str]] = {}
    for pername, viewperm, saveperm in grants:
        flags = []
        if _is_granted(saveperm):
            flags.append(SAVEPERM)
        if _is_granted(viewperm):
            flags.append(VIEWPERM)
        if flags:
            # Merge rather than overwrite: the legacy table can carry the same
            # screen twice under different casing, and hyphenating means a row
            # already spelled "mem-subgroups" now lands on the same key as
            # "mem subgroups". Either way the flags union instead of one row
            # silently winning.
            key = response_key(pername)
            granted[key] = sorted(set(granted.get(key, [])) | set(flags))
    return granted


def resource_for_pername(pername: str) -> str | None:
    """The resource slug a legacy screen name maps to, or None if unmapped."""
    return _NORMALIZED_RESOURCES.get(_normalize_pername(pername))


def permissions_from_grants(grants: Iterable[tuple[str, Any, Any]]) -> set[str]:
    """Expand ``(pername, viewperm, saveperm)`` rows into permission codes.

    Fails closed throughout: no rows, unset flags, or a screen we don't map
    (one added to `sql.userperm` after this catalog) grant nothing rather than
    raising — an unknown screen shouldn't lock a user out of the ones we do know.
    """
    perms: set[str] = set()
    for pername, viewperm, saveperm in grants:
        resource = resource_for_pername(pername)
        if resource is None:
            continue
        if _is_granted(viewperm):
            perms.add(f"{resource}:view")
            perms.update(_IMPLIED_BY_VIEW.get(resource, ()))
        if _is_granted(saveperm):
            perms.add(f"{resource}:save")
    return perms


def validate_permission_catalog() -> None:
    """Raise if any Perm code can't be granted by some screen.

    A permission no pername produces is unreachable — `require(...)` on it would
    reject every user, including superusers. Called at startup so the mismatch
    surfaces on boot instead of as a 403 in production.
    """
    grantable = permissions_from_grants(
        (pername, "Y", "Y") for pername in PERNAME_RESOURCES
    )
    orphaned = ALL_PERMISSIONS - grantable
    if orphaned:
        raise ValueError(
            "Permissions with no pername source in PERNAME_RESOURCES: "
            f"{sorted(orphaned)}"
        )


def group_permissions(perms: Iterable[str]) -> dict[str, list[str]]:
    """Permission codes regrouped as ``{resource: [actions]}`` for API responses."""
    grouped: dict[str, list[str]] = {}
    for perm in perms:
        resource, _, action = perm.partition(":")
        grouped.setdefault(resource, []).append(action)
    return {resource: sorted(actions) for resource, actions in grouped.items()}
