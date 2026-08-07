"""added location field to address model.

Revision ID: e6fce64649e3
Revises: e3f4a5b6c7d8
Create Date: 2026-08-07 05:43:43.454485

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e6fce64649e3'
down_revision: Union[str, Sequence[str], None] = 'e3f4a5b6c7d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('member_addresses', sa.Column('location', sa.String(length=10), nullable=True))

def downgrade() -> None:
    op.drop_column('member_addresses', 'location')
