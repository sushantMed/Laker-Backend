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


_existing_columns: dict[str, set[str]] = {}


def _add_column(table: str, column: sa.Column) -> None:
    """Add the column unless this database already carries it.

    A database that ran this revision while it sat on a since-deleted branch
    already has some of these columns, and adding one twice is ORA-01430. On a
    database that has none of them this behaves exactly like op.add_column.
    """
    if table not in _existing_columns:
        _existing_columns[table] = {
            c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)
        }
    if column.name in _existing_columns[table]:
        return
    op.add_column(table, column)
    _existing_columns[table].add(column.name)


def upgrade() -> None:
    _add_column('member_addresses', sa.Column('region_code', sa.String(length=20), nullable=True))



def downgrade() -> None:
    op.drop_column('member_addresses', 'region_code')
