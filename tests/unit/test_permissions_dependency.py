"""Unit tests for the `require()` dependency in app.core.permissions.

The dependency is a plain async callable once built, so these call it directly
with a UserModel instead of going through FastAPI. Endpoint wiring is covered in
tests/integration/test_claim_endpoints.py.
"""

import uuid
from typing import Annotated, get_args, get_origin

import pytest  # type: ignore
from fastapi import Depends, HTTPException  # type: ignore

from app.core.permissions import Perm, RequireUser, require
from app.models.permission_model import UserPermissionModel
from app.models.user_model import UserModel


def _user(*grants: tuple[str, str, str], status: str = "ACTIVE") -> UserModel:
    return UserModel(
        id=uuid.uuid4(),
        email="tester@example.com",
        first_name="Test",
        last_name="User",
        hashed_password="x",
        status=status,
        grants=[
            UserPermissionModel(pername=pername, viewperm=viewperm, saveperm=saveperm)
            for pername, viewperm, saveperm in grants
        ],
    )


async def test_granted_permission_passes_and_returns_the_user():
    user = _user(("drug lookup screen", "Y", "N"))
    assert await require(Perm.DRUG_VIEW)(user) is user


async def test_missing_permission_is_403_naming_the_permission():
    user = _user(("Memeber Screen", "Y", "Y"))
    with pytest.raises(HTTPException) as exc:
        await require(Perm.DRUG_VIEW)(user)
    assert exc.value.status_code == 403
    assert exc.value.detail == "Missing permission: drug:view"


async def test_user_with_no_grants_is_rejected():
    with pytest.raises(HTTPException) as exc:
        await require(Perm.CLAIM_VIEW)(_user())
    assert exc.value.status_code == 403


async def test_every_listed_permission_must_be_held():
    """Held perms are not enough — `require` is an AND, not an OR."""
    user = _user(("Paid claim lookup screen", "Y", "N"))
    with pytest.raises(HTTPException) as exc:
        await require(Perm.CLAIM_VIEW, Perm.CLAIM_SAVE)(user)
    assert exc.value.detail == "Missing permission: claim:save"


async def test_multiple_missing_permissions_are_listed_sorted():
    with pytest.raises(HTTPException) as exc:
        await require(Perm.DRUG_VIEW, Perm.CLAIM_VIEW)(_user())
    assert exc.value.detail == "Missing permission: claim:view, drug:view"


async def test_requiring_nothing_admits_any_active_user():
    user = _user()
    assert await require()(user) is user


@pytest.mark.parametrize("status", ["INACTIVE", "LOCKED", "active", ""])
async def test_non_active_status_is_rejected_even_when_permission_is_held(status):
    user = _user(("drug lookup screen", "Y", "Y"), status=status)
    with pytest.raises(HTTPException) as exc:
        await require(Perm.DRUG_VIEW)(user)
    assert exc.value.status_code == 403
    assert exc.value.detail == "Account is not active"


async def test_status_is_checked_before_permissions():
    """A deactivated user gets the account message, not a permissions hint."""
    with pytest.raises(HTTPException) as exc:
        await require(Perm.DRUG_VIEW)(_user(status="INACTIVE"))
    assert exc.value.detail == "Account is not active"


async def test_save_grant_alone_satisfies_view():
    """`saveperm` implies view, matching how /auth/me reports the grant."""
    user = _user(("drug lookup screen", "N", "Y"))
    assert await require(Perm.DRUG_SAVE)(user) is user
    assert await require(Perm.DRUG_VIEW)(user) is user


def test_require_user_is_an_annotated_user_dependency():
    annotation = RequireUser(Perm.DRUG_VIEW)
    assert get_origin(annotation) is Annotated
    model, marker = get_args(annotation)
    assert model is UserModel
    assert isinstance(marker, type(Depends(lambda: None)))
