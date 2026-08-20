"""merge drug reference and subscriber lookup branches

Revision ID: d819b99fe534
Revises: f2a3b4c5d6e7, ac348dc0d2e3
Create Date: 2026-08-20 21:30:08.827527

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd819b99fe534'
down_revision: Union[str, Sequence[str], None] = ('f2a3b4c5d6e7', 'ac348dc0d2e3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
