"""add subsnotes and subsnotestype lookup tables

Revision ID: 6d632a048669
Revises: 1f6d9663dc60
Create Date: 2026-08-21 00:00:00.000000

Creates SUBSNOTESTYPE and SUBSNOTES in whatever schema the app's DB user
defaults to (same pattern as fb380cc4a6a2 / 7e6261a14960). Column shapes
match app.models.subs_notes_type_model.SubsNotesTypeModel and
app.models.subs_notes_model.SubsNotesModel exactly. SUBSNOTESTYPE is
created first since SUBSNOTES.SUBSNOTESTYPEID references it.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '6d632a048669'
down_revision: Union[str, Sequence[str], None] = '1f6d9663dc60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "SUBSNOTESTYPE",
        sa.Column("SUBSNOTESTYPEID", sa.Numeric(), nullable=False),
        sa.Column("SUBSNOTESTYPEDESC", sa.String(length=35), nullable=True),
        sa.PrimaryKeyConstraint("SUBSNOTESTYPEID"),
    )

    op.create_table(
        "SUBSNOTES",
        sa.Column("SUBSCRIBER", sa.String(length=45), nullable=False),
        sa.Column("PC", sa.String(length=2), nullable=False),
        sa.Column("LINENUM", sa.Numeric(), nullable=False),
        sa.Column("TIMESTAMP", sa.Date(), nullable=True),
        sa.Column("DT", sa.Date(), nullable=True),
        sa.Column("NAME", sa.String(length=30), nullable=True),
        sa.Column("NOTE", sa.String(length=4000), nullable=True),
        sa.Column("SOURCE", sa.String(length=15), nullable=True),
        sa.Column("SUBSNOTESTYPEID", sa.Numeric(), nullable=True),
        sa.Column("ALERTTITLE", sa.String(length=100), nullable=True),
        sa.Column("ALERTMESSAGE", sa.String(length=1000), nullable=True),
        sa.Column("ALERTSTARTDATE", sa.Date(), nullable=True),
        sa.Column("ALERTENDDATE", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("SUBSCRIBER", "PC", "LINENUM"),
        sa.ForeignKeyConstraint(
            ["SUBSNOTESTYPEID"],
            ["SUBSNOTESTYPE.SUBSNOTESTYPEID"],
        ),
    )


def downgrade() -> None:
    op.drop_table("SUBSNOTES")
    op.drop_table("SUBSNOTESTYPE")
