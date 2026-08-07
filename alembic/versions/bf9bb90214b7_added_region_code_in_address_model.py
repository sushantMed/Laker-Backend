"""added region_code in address model.

Revision ID: bf9bb90214b7
Revises: e6fce64649e3
Create Date: 2026-08-07 13:56:16.384332

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'bf9bb90214b7'
down_revision: Union[str, Sequence[str], None] = 'e6fce64649e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('member_addresses', sa.Column('region_code', sa.String(length=20), nullable=True))



def downgrade() -> None:
    op.drop_column('member_addresses', 'region_code')
