"""restore claims.date_written

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-08-20 00:00:00.000000

ClaimModel.date_written and the claim search's startDate both depend on this
column, but a migration on a branch that no longer exists dropped it, so every
ORM query against claims raised ORA-00904. Guarded both ways: a database that
never ran that drop is left alone.

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "claims"
_COLUMN = "date_written"


def _has_column() -> bool:
    columns = sa.inspect(op.get_bind()).get_columns(_TABLE)
    return any(c["name"] == _COLUMN for c in columns)


def upgrade() -> None:
    if not _has_column():
        op.add_column(_TABLE, sa.Column(_COLUMN, sa.Date(), nullable=True))


def downgrade() -> None:
    if _has_column():
        op.drop_column(_TABLE, _COLUMN)
