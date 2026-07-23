"""multi-role RBAC: users.role -> users.roles (+ session_version)

Revision ID: c1d2e3f4a5b6
Revises: 88b907ae2b69
Create Date: 2026-07-23

Adapted for Oracle: roles are stored as a JSON column (Oracle has no native
array type and no GIN index), not the Postgres ARRAY/GIN from the original spec.

Backfill maps the old single `role` onto a one-element roles list. Any legacy
value not in the known role set (e.g. the old default "user") falls back to
["readonly"] — read-only — which is the fail-closed default.

    Before running, confirm the spread of existing values:
        SELECT role, COUNT(*) FROM users GROUP BY role;
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.database.types import JSONText

revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "88b907ae2b69"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_KNOWN_ROLES = ("admin", "members", "drugs", "readonly")
_BACKFILL_ROLES = (
    "UPDATE users SET roles = CASE "
    "WHEN role IN ('admin', 'members', 'drugs', 'readonly') "
    "THEN '[\"' || role || '\"]' "
    "ELSE '[\"readonly\"]' END"
)


def upgrade() -> None:
    # 1. Add the new columns. `roles` starts nullable so we can backfill before
    #    enforcing NOT NULL.
    op.add_column("users", sa.Column("roles", JSONText(), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "session_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )

    # 2. Backfill roles from the old single-role column.
    op.execute(_BACKFILL_ROLES)

    # 3. Now that every row has a value, enforce NOT NULL and drop `role`.
    op.alter_column("users", "roles", nullable=False)
    op.drop_column("users", "role")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(length=20),
            nullable=False,
            server_default="readonly",
        ),
    )
    # Take the first role back into the single-role column.
    op.execute("UPDATE users SET role = COALESCE(JSON_VALUE(roles, '$[0]'), 'readonly')")
    op.drop_column("users", "session_version")
    op.drop_column("users", "roles")
