"""seed user_permissions rows for the seeded accounts

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-07-29

Grants for the accounts in app/scripts/users.json, so a fresh environment has
something to exercise the screens with. Data only — no schema change.

Since d2e3f4a5b6c7 derives nothing from `users.roles`, inserts like these are
the only way anyone gets a permission. Accounts not listed here hold no grants
and can reach no screen until rows are added for them.

Users are matched by email rather than id, since ids are UUIDs minted at seed
time. Anything that doesn't line up is skipped rather than failing the migration:

  - a user in the list who isn't in this environment (the seed never ran, or the
    account was removed) is passed over,
  - a (user, screen) pair that already has a row is left as-is, so this can run
    after d2e3f4a5b6c7's role backfill without tripping
    uq_userperm_user_pername.

Both make the migration re-runnable and safe on an environment that has already
been granted by hand.

    To see what it will touch:
        SELECT email FROM users WHERE LOWER(email) IN (...);
"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "d2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Every screen, both flags. Written out rather than imported from
# app.core.rbac: a migration has to keep working when the catalog changes.
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

# email -> (pername, viewperm, saveperm). Pernames must match the canonical
# spelling in PERNAME_RESOURCES (app/core/rbac.py) — lookup tolerates casing,
# but /auth/me echoes these strings straight back to the client.
# 16 admin rows + 20 demo rows.
_GRANTS: dict[str, tuple[tuple[str, str, str], ...]] = {
    # d2e3f4a5b6c7 no longer backfills from roles, so this is the only thing
    # granting the "user admin" screen — without it GET /users/{id} is
    # unreachable by anyone.
    "admin@example.com": tuple((screen, "Y", "Y") for screen in _ALL_SCREENS),
    # Member servicing: full member screen, read-only everywhere else.
    "user@example.com": (
        ("Memeber Screen", "Y", "Y"),
        ("Paid claim lookup screen", "Y", "N"),
        ("membercob", "Y", "N"),
        ("member prior auth", "Y", "N"),
        ("web member dependents", "Y", "N"),
        ("pricing", "Y", "N"),
    ),
    # Read-only analyst: view on the lookup/reporting screens, no saves at all.
    "sushant.sinha@businessonetech.com": (
        ("Memeber Screen", "Y", "N"),
        ("Paid claim lookup screen", "Y", "N"),
        ("mem subgroups", "Y", "N"),
        ("memdenynotes", "Y", "N"),
        ("tran lookup screen", "Y", "N"),
        ("web accum", "Y", "N"),
        ("groups screen", "Y", "N"),
    ),
    # Card/eligibility handling: saves on the two screens that need it.
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

    Same reason as in d2e3f4a5b6c7: sa.text() carries no type information, so
    Oracle returns the raw CHAR(32) hex string and sa.Uuid's bind processor
    needs a real UUID object.
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
    """(user_id, normalized pername) pairs already present, so a re-run or a
    prior backfill doesn't collide with uq_userperm_user_pername."""
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
            continue  # account not in this environment
        for pername, viewperm, saveperm in grants:
            if (user_id, pername.strip().lower()) in existing:
                continue  # already granted; don't clobber what's there
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
    """Remove only the (user, screen) pairs this migration lists.

    Rows upgrade() skipped as pre-existing are deleted too — they can't be told
    apart from ones it inserted. That is the safe direction for a downgrade of a
    grant: it revokes access rather than leaving it behind.
    """
    bind = op.get_bind()
    ids = _user_ids_by_email(bind)

    for email, grants in _GRANTS.items():
        user_id = ids.get(email)
        if user_id is None:
            continue
        # Deleted through the typed table, not sa.text(): sa.Uuid stores the id
        # as 32-char hex, so a str(uuid) bind — which carries dashes — matches
        # nothing at all and the downgrade silently no-ops.
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
