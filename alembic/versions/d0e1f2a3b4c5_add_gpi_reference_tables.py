"""add gpi reference tables

Revision ID: d0e1f2a3b4c5
Revises: c9f1a2b3d4e5
Create Date: 2026-08-20 00:00:00.000000

GpiDesc names a full 14-character GPI, GpiList a partial one (keyed with a
leading "G"). Column widths are inferred -- the legacy DDL was not supplied.

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, Sequence[str], None] = "c9f1a2b3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gpidesc",
        sa.Column("gpi", sa.String(length=14), nullable=False),
        sa.Column("gpigenname", sa.String(length=60), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_gpidesc_gpi"), "gpidesc", ["gpi"], unique=True)

    op.create_table(
        "gpilist",
        sa.Column("gpi", sa.String(length=15), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_gpilist_gpi"), "gpilist", ["gpi"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_gpilist_gpi"), table_name="gpilist")
    op.drop_table("gpilist")
    op.drop_index(op.f("ix_gpidesc_gpi"), table_name="gpidesc")
    op.drop_table("gpidesc")
