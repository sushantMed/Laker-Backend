"""remove date_written from claims

Revision ID: 45786fd73175
Revises: c85598e61b5a
Create Date: 2026-08-18 14:53:12.400146

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '45786fd73175'
down_revision: Union[str, Sequence[str], None] = 'c85598e61b5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('claims', 'date_written')


def downgrade() -> None:
    op.add_column('claims', sa.Column('date_written', sa.Date(), nullable=True))
