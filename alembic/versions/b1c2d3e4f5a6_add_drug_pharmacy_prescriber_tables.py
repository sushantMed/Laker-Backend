"""add drug pharmacy prescriber tables

Revision ID: b1c2d3e4f5a6
Revises: 0a3054329f6f
Create Date: 2026-06-18 06:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "0a3054329f6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "drugs",
        sa.Column("ndc", sa.String(length=11), nullable=False),
        sa.Column("gpi", sa.String(length=14), nullable=False),
        sa.Column("drug_name", sa.String(length=255), nullable=False),
        sa.Column(
            "brand_generic",
            sa.Enum("BRAND", "GENERIC", name="brandgeneric"),
            nullable=False,
        ),
        sa.Column(
            "maintenance",
            sa.Enum("YES", "NO", name="maintenance"),
            nullable=False,
        ),
        sa.Column("desi", sa.String(length=255), nullable=True),
        sa.Column("tier", sa.Integer(), nullable=True),
        sa.Column("formulary_status", sa.String(length=100), nullable=True),
        sa.Column("repackage_ind", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_drugs_ndc"), "drugs", ["ndc"], unique=True)
    op.create_index(op.f("ix_drugs_gpi"), "drugs", ["gpi"], unique=False)

    op.create_table(
        "pharmacies",
        sa.Column("nabp", sa.String(length=7), nullable=False),
        sa.Column("npi", sa.String(length=10), nullable=False),
        sa.Column("pharmacy_name", sa.String(length=255), nullable=False),
        sa.Column("address_line1", sa.String(length=255), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=2), nullable=False),
        sa.Column("zip", sa.String(length=10), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("fax", sa.String(length=20), nullable=True),
        sa.Column("is_24_hour", sa.Boolean(), nullable=False),
        sa.Column("in_network", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pharmacies_nabp"), "pharmacies", ["nabp"], unique=True)
    op.create_index(op.f("ix_pharmacies_npi"), "pharmacies", ["npi"], unique=False)

    op.create_table(
        "prescribers",
        sa.Column("npi", sa.String(length=10), nullable=False),
        sa.Column("dea", sa.String(length=9), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("specialty", sa.String(length=100), nullable=True),
        sa.Column("address_line1", sa.String(length=255), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=2), nullable=False),
        sa.Column("zip", sa.String(length=10), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("fax", sa.String(length=20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_prescribers_npi"), "prescribers", ["npi"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_prescribers_npi"), table_name="prescribers")
    op.drop_table("prescribers")
    op.drop_index(op.f("ix_pharmacies_npi"), table_name="pharmacies")
    op.drop_index(op.f("ix_pharmacies_nabp"), table_name="pharmacies")
    op.drop_table("pharmacies")
    op.drop_index(op.f("ix_drugs_gpi"), table_name="drugs")
    op.drop_index(op.f("ix_drugs_ndc"), table_name="drugs")
    op.drop_table("drugs")
    sa.Enum(name="brandgeneric").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="maintenance").drop(op.get_bind(), checkfirst=True)
