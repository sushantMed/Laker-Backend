"""drop the drugs.tier column

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-08-06

Tier is no longer part of the drug record or the drug search criteria.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, Sequence[str], None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("drugs", "tier")


def downgrade() -> None:
    op.add_column("drugs", sa.Column("tier", sa.Integer(), nullable=True))
