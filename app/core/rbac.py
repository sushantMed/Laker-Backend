"""Permissions, sourced from the `user_permissions` rows a user holds."""

import re
from collections.abc import Iterable
from typing import Any

VIEW = "view"
SAVE = "save"


class Perm:
    DRUG_VIEW = "drug:view"
    DRUG_SAVE = "drug:save"
    GROUPS_VIEW = "groups:view"
    GROUPS_SAVE = "groups:save"
    USERADMIN_VIEW = "useradmin:view"
    USERADMIN_SAVE = "useradmin:save"

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


# Screen name -> resource slug. Keys match the spelling in `sql.userperm`,
# typos included; lookups are case- and whitespace-insensitive.
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

# Extra permissions a `viewperm` grant carries beyond `<resource>:view`.
_IMPLIED_BY_VIEW: dict[str, tuple[str, ...]] = {
    "member": (Perm.MEMBER_SEARCH, Perm.MEMBER_SEARCH_PREVCARDID),
}

# Flag values that count as granted. Anything else fails closed.
_GRANTED_FLAGS = frozenset({"y", "1", "true"})

_WHITESPACE = re.compile(r"\s+")


def _normalize_pername(pername: str) -> str:
    return _WHITESPACE.sub(" ", str(pername)).strip().lower()


def response_key(pername: str) -> str:
    """A pername as /auth/me spells it: whitespace joined with '-'.

    Presentation only -- "Memeber Screen" becomes "Memeber-Screen". Not used for
    lookups; grants are matched via resource_for_pername().
    """
    return _WHITESPACE.sub("-", str(pername).strip())


_NORMALIZED_RESOURCES: dict[str, str] = {
    _normalize_pername(pername): resource
    for pername, resource in PERNAME_RESOURCES.items()
}


def _is_granted(flag: Any) -> bool:
    return str(flag).strip().lower() in _GRANTED_FLAGS


def grant_map(grants: Iterable[tuple[str, Any, Any]]) -> dict[str, list[str]]:
    """The user's grants as ``{screen: [granted actions]}``, e.g.

        {"Memeber-Screen": ["save", "view"], "pricing": ["view"]}

    ``saveperm`` implies view, so a save grant reports both actions. Screens with
    neither flag set are omitted. Unmapped screens are kept.
    """
    granted: dict[str, list[str]] = {}
    for pername, viewperm, saveperm in grants:
        flags = []
        if _is_granted(saveperm):
            flags.extend((SAVE, VIEW))
        if _is_granted(viewperm):
            flags.append(VIEW)
        if flags:
            # Two rows can collapse to the same key, so union instead of
            # overwriting.
            key = response_key(pername)
            granted[key] = sorted(set(granted.get(key, [])) | set(flags))
    return granted


def resource_for_pername(pername: str) -> str | None:
    """The resource slug a legacy screen name maps to, or None if unmapped."""
    return _NORMALIZED_RESOURCES.get(_normalize_pername(pername))


def permissions_from_grants(grants: Iterable[tuple[str, Any, Any]]) -> set[str]:
    """Expand ``(pername, viewperm, saveperm)`` rows into permission codes.

    Unmapped screens and unset flags grant nothing rather than raising.
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

    Such a permission is unreachable and would reject every user. Called at
    startup so the mismatch shows up on boot rather than as a 403 later.
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
