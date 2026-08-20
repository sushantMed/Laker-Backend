"""added precison in lat and log

Revision ID: c85598e61b5a
Revises: 2d1fe5c6f3c8
Create Date: 2026-08-18 09:45:28.540550

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import oracle

revision: str = 'c85598e61b5a'
down_revision: Union[str, Sequence[str], None] = '2d1fe5c6f3c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE pharmacies SET LATITUDE = NULL, LONGITUDE = NULL")
    op.alter_column(
        'pharmacies', 'LATITUDE',
        existing_type=sa.Numeric(),
        type_=sa.Numeric(precision=9, scale=6),
        existing_nullable=True,
    )
    op.alter_column(
        'pharmacies', 'LONGITUDE',
        existing_type=sa.Numeric(),
        type_=sa.Numeric(precision=9, scale=6),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'pharmacies', 'LATITUDE',
        existing_type=sa.Numeric(precision=9, scale=6),
        type_=sa.Numeric(),
        existing_nullable=True,
    )
    op.alter_column(
        'pharmacies', 'LONGITUDE',
        existing_type=sa.Numeric(precision=9, scale=6),
        type_=sa.Numeric(),
        existing_nullable=True,
    )
