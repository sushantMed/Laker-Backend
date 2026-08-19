"""add legacy lookup tables subscribergrouplist subscribereliglist groups

Revision ID: 6aec3e73d0c2
Revises: 45786fd73175
Create Date: 2026-08-19 11:30:38.223702

Creates SUBSCRIBERGROUPLIST, SUBSCRIBERELIGLIST, and GROUPS in whatever
schema the app's DB user defaults to (no explicit schema, matching the
current models) -- this dev database has no separate SQLMGR schema, so
these lookup tables need to actually exist here to be queryable, the same
way drugs/pharmacies/prescribers were added in b1c2d3e4f5a6.

Column shapes match app/models/subscriber_group_list_model.py,
app/models/subscriber_elig_list_model.py, and app/models/groups_model.py
exactly. SUBSCRIBERELIGLIST mirrors the real SQLMGR DDL provided for it;
SUBSCRIBERGROUPLIST and GROUPS are inferred from the legacy VB source
ported this session (GROUPS is intentionally minimal -- only the columns
actually read: GROUPNUM, BITFLAGS2).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '6aec3e73d0c2'
down_revision: Union[str, Sequence[str], None] = '45786fd73175'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "SUBSCRIBERGROUPLIST",
        sa.Column("SUBSCRIBER", sa.String(length=45), nullable=False),
        sa.Column("CLIENTCODE", sa.String(length=10), nullable=False),
        sa.Column("LINENUM", sa.Numeric(), nullable=False),
        sa.Column("GROUPNUM", sa.String(length=20), nullable=True),
        sa.Column("PRIORITY", sa.Numeric(), nullable=True),
        sa.Column("STARTDT", sa.Date(), nullable=True),
        sa.Column("ENDDT", sa.Date(), nullable=True),
        sa.Column("COVTYPE", sa.String(length=10), nullable=True),
        sa.Column("CHANGEDT", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("SUBSCRIBER", "CLIENTCODE", "LINENUM"),
    )
    op.create_index(
        op.f("ix_SUBSCRIBERGROUPLIST_GROUPNUM"),
        "SUBSCRIBERGROUPLIST",
        ["GROUPNUM"],
        unique=False,
    )

    op.create_table(
        "SUBSCRIBERELIGLIST",
        sa.Column("SUBSCRIBER", sa.String(length=45), nullable=False),
        sa.Column("PERSONCODE", sa.String(length=2), nullable=False),
        sa.Column("CLIENTCODE", sa.String(length=10), nullable=False),
        sa.Column("LINENUM", sa.Numeric(), nullable=False),
        sa.Column("STARTDT", sa.Date(), nullable=True),
        sa.Column("ENDDT", sa.Date(), nullable=True),
        sa.Column("CHANGEDT", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("SUBSCRIBER", "PERSONCODE", "CLIENTCODE", "LINENUM"),
    )

    op.create_table(
        "GROUPS",
        sa.Column("GROUPNUM", sa.String(length=20), nullable=False),
        sa.Column("BITFLAGS2", sa.Numeric(), nullable=True),
        sa.PrimaryKeyConstraint("GROUPNUM"),
    )


def downgrade() -> None:
    op.drop_table("GROUPS")
    op.drop_table("SUBSCRIBERELIGLIST")
    op.drop_index(
        op.f("ix_SUBSCRIBERGROUPLIST_GROUPNUM"), table_name="SUBSCRIBERGROUPLIST"
    )
    op.drop_table("SUBSCRIBERGROUPLIST")
