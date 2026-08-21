"""add net and netlist tables

Revision ID: 1f6d9663dc60
Revises: ac348dc0d2e3
Create Date: 2026-08-21 00:00:00.000000

Creates NET and NETLIST, mirroring the legacy SQLMGR.NET / NETLIST tables
exactly. NETLIST rows gate which pharmacies are eligible for a zip-radius
search (by NABP under TYPE 'P', or by chain AFFILIATIONCODE under TYPE
'C') -- see PharmacyRepository.get_by_zip_code, ported from the legacy
PharmacySearchResults.GetSearchData VB query this session.

Column shapes match app/models/net_model.py and app/models/netlist_model.py
exactly.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1f6d9663dc60'
down_revision: Union[str, Sequence[str], None] = 'ac348dc0d2e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "net",
        sa.Column("NETNAME", sa.String(length=30), nullable=False),
        sa.Column("CLIENT", sa.String(length=10), nullable=False),
        sa.Column("NETNUM", sa.Numeric(), nullable=True),
        sa.Column("DATECHANGED", sa.Date(), nullable=True),
        sa.Column("NETDESCRIPTION", sa.String(length=500), nullable=True),
        sa.Column("NETPM", sa.String(length=50), nullable=True),
        sa.Column("PHARMNETCATEGORY", sa.String(length=20), nullable=True),
        sa.Column("PROCESSCONTROLNUMBER", sa.String(length=10), nullable=True),
        sa.Column("RESTRICTTYPE", sa.String(length=1), nullable=True),
        sa.Column("RESTRICTVALUE", sa.String(length=20), nullable=True),
        sa.Column("OPENTIME", sa.String(length=4), nullable=True),
        sa.Column("CLOSETIME", sa.String(length=4), nullable=True),
        sa.Column("BITFLAGS", sa.Numeric(), nullable=True),
        sa.Column("NETTYPE", sa.String(length=3), nullable=True),
        sa.Column("FINAL_COMPARE_YN", sa.String(length=1), nullable=True),
        sa.PrimaryKeyConstraint("NETNAME", "CLIENT"),
        sa.UniqueConstraint("NETNUM"),
    )

    op.create_table(
        "netlist",
        sa.Column("NETNUM", sa.Numeric(), nullable=False),
        sa.Column("LINENUM", sa.Numeric(), nullable=False),
        sa.Column("TYPE", sa.String(length=1), nullable=True),
        sa.Column("VALUE", sa.String(length=30), nullable=True),
        sa.Column("INC", sa.String(length=1), nullable=True),
        sa.Column("STARTDT", sa.Date(), nullable=True),
        sa.Column("ENDDT", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(
            ["NETNUM"], ["net.NETNUM"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("NETNUM", "LINENUM"),
    )


def downgrade() -> None:
    op.drop_table("netlist")
    op.drop_table("net")
