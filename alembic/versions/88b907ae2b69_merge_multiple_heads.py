"""merge multiple heads

Revision ID: 88b907ae2b69
Revises: b1c2d3e4f5a6, bc8958dad29d
Create Date: 2026-06-24 07:24:31.932543

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '88b907ae2b69'
down_revision: Union[str, Sequence[str], None] = ('b1c2d3e4f5a6', 'bc8958dad29d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
