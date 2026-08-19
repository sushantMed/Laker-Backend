"""add subscob and subssubgroups lookup tables

Revision ID: 7e6261a14960
Revises: fb380cc4a6a2
Create Date: 2026-08-19 16:22:57.643992

Creates SUBSCOB and SUBSSUBGROUPS in whatever schema the app's DB user
defaults to (same pattern as fb380cc4a6a2 / 6aec3e73d0c2). Column shapes
match the real SQLMGR DDL provided for both tables exactly, including that
SUBSSUBGROUPS has no primary key in the source DDL -- see the comment on
app.models.subs_subgroups_model.SubsSubgroupsModel for how the ORM copes
with that.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7e6261a14960'
down_revision: Union[str, Sequence[str], None] = 'fb380cc4a6a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "SUBSCOB",
        sa.Column("SUBSCRIBER", sa.String(length=45), nullable=False),
        sa.Column("PC", sa.String(length=2), nullable=False),
        sa.Column("LINENUM", sa.Numeric(), nullable=False),
        sa.Column("OCFLAG", sa.String(length=1), nullable=True),
        sa.Column("STARTDT", sa.Date(), nullable=True),
        sa.Column("ENDDT", sa.Date(), nullable=True),
        sa.Column("COVNOTE", sa.String(length=100), nullable=True),
        sa.Column("PRIMARYINSURANCEID", sa.String(length=18), nullable=True),
        sa.Column("BIN", sa.String(length=6), nullable=True),
        sa.Column("PCN", sa.String(length=10), nullable=True),
        sa.Column("GROUPNUM", sa.String(length=15), nullable=True),
        sa.Column("PAYOR", sa.String(length=40), nullable=True),
        sa.Column("OTHERID", sa.String(length=18), nullable=True),
        sa.Column("LASTCHANGED", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("SUBSCRIBER", "PC", "LINENUM"),
    )

    op.create_table(
        "SUBSSUBGROUPS",
        sa.Column("SUBSCRIBER", sa.String(length=45), nullable=True),
        sa.Column("PC", sa.String(length=2), nullable=True),
        sa.Column("LINENUM", sa.Numeric(), nullable=True),
        sa.Column("SUBGROUP", sa.String(length=20), nullable=True),
        sa.Column("STARTDT", sa.Date(), nullable=True),
        sa.Column("ENDDT", sa.Date(), nullable=True),
        sa.Column("LASTCHANGED", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("SUBSSUBGROUPS")
    op.drop_table("SUBSCOB")
