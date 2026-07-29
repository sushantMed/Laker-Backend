"""per-user screen permissions: user_permissions table

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-07-28

Creates a table shaped like the legacy `sql.userperm`: one row per screen
(`pername`) with `viewperm` / `saveperm` flags, granted directly to a user.

No backfill from `users.roles` — grants are inserted as data, see e3f4a5b6c7d8.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, Sequence[str], None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_permissions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pername", sa.String(length=60), nullable=False),
        sa.Column("viewperm", sa.String(length=1), nullable=False, server_default="N"),
        sa.Column("saveperm", sa.String(length=1), nullable=False, server_default="N"),
        sa.UniqueConstraint("user_id", "pername", name="uq_userperm_user_pername"),
        sa.CheckConstraint("viewperm IN ('Y','N')", name="ck_userperm_viewperm_yn"),
        sa.CheckConstraint("saveperm IN ('Y','N')", name="ck_userperm_saveperm_yn"),
    )
    op.create_index("ix_user_permissions_user_id", "user_permissions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_permissions_user_id", table_name="user_permissions")
    op.drop_table("user_permissions")
