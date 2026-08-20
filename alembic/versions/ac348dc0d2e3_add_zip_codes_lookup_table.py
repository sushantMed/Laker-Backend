"""add zip codes lookup table

Revision ID: ac348dc0d2e3
Revises: 7e6261a14960
Create Date: 2026-08-20 00:00:00.000000

Adds ZIPCODES, mirroring the legacy sqlmgr.ZIPCODES reference table exactly.
Radius searches (e.g. pharmacy lookup) resolve the search origin from this
table instead of averaging coordinates off of whichever target-table rows
happen to share the entered ZIP.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'ac348dc0d2e3'
down_revision: Union[str, Sequence[str], None] = '7e6261a14960'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ZIPCODES",
        sa.Column("ZIP", sa.String(length=5), nullable=False),
        sa.Column("CITY", sa.String(length=45), nullable=True),
        sa.Column("ABBREVIATION", sa.String(length=13), nullable=True),
        sa.Column("COUNTYNAME", sa.String(length=40), nullable=True),
        sa.Column("STATENAME", sa.String(length=28), nullable=True),
        sa.Column("STATE", sa.String(length=2), nullable=True),
        sa.Column("CITYTYPE", sa.String(length=1), nullable=True),
        sa.Column("ZIPTYPE", sa.String(length=1), nullable=True),
        sa.Column("FIPS", sa.Numeric(precision=5, scale=0), nullable=True),
        sa.Column("AREACODE", sa.Numeric(precision=3, scale=0), nullable=True),
        sa.Column("OVERLAY", sa.String(length=50), nullable=True),
        sa.Column("TIMEZONE", sa.String(length=2), nullable=True),
        sa.Column("DST", sa.String(length=1), nullable=True),
        sa.Column("UTC", sa.String(length=15), nullable=True),
        sa.Column("LATITUDE", sa.Numeric(precision=12, scale=7), nullable=True),
        sa.Column("LONGITUDE", sa.Numeric(precision=12, scale=7), nullable=True),
        sa.PrimaryKeyConstraint("ZIP"),
    )


def downgrade() -> None:
    op.drop_table("ZIPCODES")
