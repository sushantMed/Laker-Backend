import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, field_validator


class Perm:
    DRUG_VIEW = "drug:view"
    GROUPS_VIEW = "groups:view"
    MEMBER_VIEW = "member:view"
    MEMBER_SAVE = "member:save"
    MEMBER_SEARCH = "member:search"
    MEMBER_SEARCH_PREVCARDID = "member:searchwithprevcardid"
    CLAIM_VIEW = "claim:view"


ALL_PERMISSIONS: set[str] = {
    v for k, v in vars(Perm).items() if not k.startswith("_") and isinstance(v, str)
}


class RoleDef(BaseModel):
    description: str = ""
    superuser: bool = False
    permissions: set[str] = set()

    @field_validator("permissions")
    @classmethod
    def known_perms(cls, v: set[str]) -> set[str]:
        unknown = v - ALL_PERMISSIONS
        if unknown:
            raise ValueError(f"Unknown permissions in roles.json: {sorted(unknown)}")
        return v


ROLES_PATH = Path(__file__).resolve().parent.parent / "config" / "roles.json"


@lru_cache(maxsize=1)
def load_roles() -> dict[str, RoleDef]:
    """Parse and validate roles.json once. A malformed file raises here."""
    raw = json.loads(ROLES_PATH.read_text(encoding="utf-8"))
    return {name: RoleDef(**cfg) for name, cfg in raw.items()}


def resolve_permissions(role_names: list[str] | None) -> set[str]:
    """Union of permissions granted by the given roles. Fails closed."""
    if not role_names:
        return set()
    defs = load_roles()
    matched = [defs[n] for n in role_names if n in defs]
    if not matched:
        return set()  # unknown role name(s) -> zero permissions
    if any(d.superuser for d in matched):
        return set(ALL_PERMISSIONS)
    return set().union(*(d.permissions for d in matched))
