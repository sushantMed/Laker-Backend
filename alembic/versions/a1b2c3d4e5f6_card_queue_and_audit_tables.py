"""card print queue (cardq) and legacy audit trail (updtran/updtrandetail)"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "45786fd73175"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cardq",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("key", sa.Numeric(), nullable=False),
        sa.Column("subscriber", sa.String(length=45), nullable=True),
        sa.Column("personcode", sa.String(length=2), nullable=True),
        sa.Column("tablename", sa.String(length=30), nullable=True),
        sa.Column("fieldname", sa.String(length=30), nullable=True),
        sa.Column("oldvalue", sa.String(length=100), nullable=True),
        sa.Column("newvalue", sa.String(length=100), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("printdate", sa.Date(), nullable=True),
        sa.Column("batchnum", sa.Numeric(), nullable=True),
        sa.Column("reportstatus", sa.String(length=7), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cardq_key"), "cardq", ["key"], unique=True)
    op.create_index(
        "ix_cardq_subscriber_personcode", "cardq", ["subscriber", "personcode"]
    )
    op.create_index("ix_cardq_timestamp", "cardq", ["timestamp"])
    op.create_index("ix_cardq_batchnum", "cardq", ["batchnum"])

    op.create_table(
        "updtran",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("trankey", sa.Numeric(), nullable=False),
        sa.Column("clientcode", sa.String(length=10), nullable=True),
        sa.Column("tranid", sa.Numeric(), nullable=True),
        sa.Column("screenid", sa.Numeric(), nullable=True),
        sa.Column("screenkey", sa.String(length=50), nullable=True),
        sa.Column("userid", sa.String(length=15), nullable=True),
        sa.Column("trants", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        # Must be a constraint rather than a unique index -- Oracle rejects a
        # foreign key that references an index-only unique column (ORA-02270).
        sa.UniqueConstraint("trankey", name="uq_updtran_trankey"),
    )
    op.create_index(
        "ix_updtran_clientcode_screenkey", "updtran", ["clientcode", "screenkey"]
    )

    op.create_table(
        "updtrandetail",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("trankey", sa.Numeric(), nullable=False),
        sa.Column("linenum", sa.Numeric(), nullable=False),
        sa.Column("detailkey", sa.String(length=35), nullable=True),
        sa.Column("updtable", sa.String(length=25), nullable=True),
        sa.Column("fieldname", sa.String(length=20), nullable=True),
        sa.Column("newvalue", sa.String(length=200), nullable=True),
        sa.Column("oldvalue", sa.String(length=200), nullable=True),
        sa.Column("txnum", sa.Numeric(), nullable=True),
        sa.Column("seqnum", sa.Numeric(), nullable=True),
        sa.ForeignKeyConstraint(["trankey"], ["updtran.trankey"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_updtrandetail_trankey"), "updtrandetail", ["trankey"])
    op.create_index(
        "ix_updtrandetail_trankey_linenum",
        "updtrandetail",
        ["trankey", "linenum"],
        unique=True,
    )
    op.create_index(
        "ix_updtrandetail_updtable_detailkey",
        "updtrandetail",
        ["updtable", "detailkey"],
    )


def downgrade() -> None:
    op.drop_index("ix_updtrandetail_updtable_detailkey", table_name="updtrandetail")
    op.drop_index("ix_updtrandetail_trankey_linenum", table_name="updtrandetail")
    op.drop_index(op.f("ix_updtrandetail_trankey"), table_name="updtrandetail")
    op.drop_table("updtrandetail")

    op.drop_index("ix_updtran_clientcode_screenkey", table_name="updtran")
    op.drop_table("updtran")

    op.drop_index("ix_cardq_batchnum", table_name="cardq")
    op.drop_index("ix_cardq_timestamp", table_name="cardq")
    op.drop_index("ix_cardq_subscriber_personcode", table_name="cardq")
    op.drop_index(op.f("ix_cardq_key"), table_name="cardq")
    op.drop_table("cardq")
