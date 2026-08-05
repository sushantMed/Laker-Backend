"""seed user_permissions rows for the seeded accounts

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-07-29

Grants for the accounts in app/scripts/users.json. Data only, no schema change.

Users are matched by email since ids are minted at seed time. Missing accounts
and already-granted pairs are skipped, so this is re-runnable.
"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "d2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Listed here rather than imported from app.core.rbac so the migration keeps
# working when the catalog changes.
_ALL_SCREENS = (
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
    "drug lookup screen",
    "groups screen",
    "user admin",
)

# email -> (pername, viewperm, saveperm). Pernames must match the spelling in
# PERNAME_RESOURCES (app/core/rbac.py); /auth/me echoes them back to the client.
_GRANTS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "admin@example.com": tuple((screen, "Y", "Y") for screen in _ALL_SCREENS),
    # Member servicing: full member screen, read-only elsewhere.
    "user@example.com": (
        ("Memeber Screen", "Y", "Y"),
        ("Paid claim lookup screen", "Y", "N"),
        ("membercob", "Y", "N"),
        ("member prior auth", "Y", "N"),
        ("web member dependents", "Y", "N"),
        ("pricing", "Y", "N"),
    ),
    # Read-only analyst: view on the lookup/reporting screens.
    "sushant.sinha@businessonetech.com": (
        ("Memeber Screen", "Y", "N"),
        ("Paid claim lookup screen", "Y", "N"),
        ("mem subgroups", "Y", "N"),
        ("memdenynotes", "Y", "N"),
        ("tran lookup screen", "Y", "N"),
        ("web accum", "Y", "N"),
        ("groups screen", "Y", "N"),
    ),
    # Card/eligibility handling.
    "dhanush@hotmail.com": (
        ("Memeber Screen", "Y", "Y"),
        ("Mem cancel Card Request", "Y", "Y"),
        ("mem term date limit", "Y", "N"),
        ("subs prescriber restrict", "Y", "N"),
        ("drug lookup screen", "Y", "N"),
        ("pricing", "Y", "N"),
        ("tran lookup screen", "Y", "N"),
    ),
}

_user_permissions = sa.table(
    "user_permissions",
    sa.column("id", sa.Uuid(as_uuid=True)),
    sa.column("user_id", sa.Uuid(as_uuid=True)),
    sa.column("pername", sa.String(60)),
    sa.column("viewperm", sa.String(1)),
    sa.column("saveperm", sa.String(1)),
)


def _as_uuid(value) -> uuid.UUID:
    """Coerce a users.id back into a UUID.

    sa.text() carries no type information, so Oracle returns the raw CHAR(32)
    hex string while sa.Uuid's bind processor needs a real UUID object.
    """
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value).strip())


def _user_ids_by_email(bind) -> dict[str, uuid.UUID]:
    """Resolve the listed emails to ids, keyed by lowercase email."""
    rows = bind.execute(sa.text("SELECT id, email FROM users")).fetchall()
    wanted = set(_GRANTS)
    return {
        str(email).strip().lower(): _as_uuid(user_id)
        for user_id, email in rows
        if str(email).strip().lower() in wanted
    }


def _existing_pairs(bind) -> set[tuple[uuid.UUID, str]]:
    """(user_id, normalized pername) pairs already present."""
    rows = bind.execute(
        sa.text("SELECT user_id, pername FROM user_permissions")
    ).fetchall()
    return {(_as_uuid(user_id), str(pername).strip().lower()) for user_id, pername in rows}


def upgrade() -> None:
    bind = op.get_bind()
    ids = _user_ids_by_email(bind)
    existing = _existing_pairs(bind)

    rows = []
    for email, grants in _GRANTS.items():
        user_id = ids.get(email)
        if user_id is None:
            continue
        for pername, viewperm, saveperm in grants:
            if (user_id, pername.strip().lower()) in existing:
                continue
            rows.append(
                {
                    "id": uuid.uuid4(),
                    "user_id": user_id,
                    "pername": pername,
                    "viewperm": viewperm,
                    "saveperm": saveperm,
                }
            )

    if rows:
        op.bulk_insert(_user_permissions, rows)


def downgrade() -> None:
    """Remove the (user, screen) pairs this migration lists.

    Pre-existing rows go too, since they can't be told apart from inserted ones.
    """
    bind = op.get_bind()
    ids = _user_ids_by_email(bind)

    for email, grants in _GRANTS.items():
        user_id = ids.get(email)
        if user_id is None:
            continue
        # Through the typed table, not sa.text(): sa.Uuid stores the id as
        # 32-char hex, so a str(uuid) bind carries dashes and matches nothing.
        bind.execute(
            _user_permissions.delete().where(
                sa.and_(
                    _user_permissions.c.user_id == user_id,
                    sa.func.lower(_user_permissions.c.pername).in_(
                        [pername.strip().lower() for pername, _, _ in grants]
                    ),
                )
            )
        )
