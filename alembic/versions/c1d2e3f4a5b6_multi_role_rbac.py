"""multi-role RBAC: users.role -> users.roles (+ session_version)

Revision ID: c1d2e3f4a5b6
Revises: 88b907ae2b69
Create Date: 2026-07-23

Roles are stored as a JSON column since Oracle has no native array type.
Backfill maps the old single `role` onto a one-element list; unknown values
fall back to ["readonly"].
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
    # Nullable at first so it can be backfilled before NOT NULL is enforced.
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

    op.execute(_BACKFILL_ROLES)

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
    op.execute("UPDATE users SET role = COALESCE(JSON_VALUE(roles, '$[0]'), 'readonly')")
    op.drop_column("users", "session_version")
    op.drop_column("users", "roles")
