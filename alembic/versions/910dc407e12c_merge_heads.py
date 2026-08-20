"""merge heads

Revision ID: 910dc407e12c
Revises: 2d27b194a8e4, a5b6c7d8e9f0
Create Date: 2026-08-13 11:54:09.456802

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '910dc407e12c'
down_revision: Union[str, Sequence[str], None] = ('2d27b194a8e4', 'a5b6c7d8e9f0')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
