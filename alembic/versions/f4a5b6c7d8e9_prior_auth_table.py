from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, Sequence[str], None] = "e6fce64649e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "prior_auths",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("authnum", sa.Numeric(), nullable=False),
        sa.Column("subscribernum", sa.String(length=45), nullable=True),
        sa.Column("groupnum", sa.String(length=20), nullable=True),
        sa.Column("personcodes", sa.String(length=50), nullable=True),
        sa.Column("effdate", sa.Date(), nullable=True),
        sa.Column("termdate", sa.Date(), nullable=True),
        sa.Column("providerid", sa.String(length=30), nullable=True),
        sa.Column("prescriberid", sa.String(length=15), nullable=True),
        sa.Column("ndc", sa.String(length=11), nullable=True),
        sa.Column("gpi", sa.String(length=14), nullable=True),
        sa.Column("bg", sa.String(length=1), nullable=True),
        sa.Column("action", sa.String(length=1), nullable=True),
        sa.Column("bitflags", sa.Numeric(), nullable=True),
        sa.Column("treatmony", sa.String(length=1), nullable=True),
        sa.Column("costhandler", sa.String(length=20), nullable=True),
        sa.Column("dispfeehandler", sa.String(length=20), nullable=True),
        sa.Column("copayhandler", sa.String(length=20), nullable=True),
        sa.Column("brandflatcopay", sa.String(length=10), nullable=True),
        sa.Column("genericflatcopay", sa.String(length=10), nullable=True),
        sa.Column("treatpharmnet", sa.String(length=30), nullable=True),
        sa.Column("treatphysnet", sa.String(length=20), nullable=True),
        sa.Column("maxdailydose", sa.String(length=5), nullable=True),
        sa.Column("maxscriptqty", sa.String(length=10), nullable=True),
        sa.Column("maxscriptdays", sa.String(length=5), nullable=True),
        sa.Column("maxscriptdollars", sa.String(length=10), nullable=True),
        sa.Column("createuser", sa.String(length=20), nullable=True),
        sa.Column("createts", sa.DateTime(), nullable=True),
        sa.Column("changeuser", sa.String(length=20), nullable=True),
        sa.Column("changets", sa.DateTime(), nullable=True),
        sa.Column("reasoncode", sa.String(length=20), nullable=True),
        sa.Column("notes", sa.String(length=4000), nullable=True),
        sa.Column("deaclass", sa.String(length=9), nullable=True),
        sa.Column("ignorepm", sa.String(length=55), nullable=True),
        sa.Column("genname", sa.String(length=60), nullable=True),
        sa.Column("therclass", sa.String(length=10), nullable=True),
        sa.Column("refills", sa.String(length=4), nullable=True),
        sa.Column("message", sa.String(length=100), nullable=True),
        sa.Column("source", sa.String(length=10), nullable=True),
        sa.Column("authby", sa.String(length=50), nullable=True),
        sa.Column("includepm", sa.String(length=55), nullable=True),
        sa.Column("includepmcolor", sa.String(length=1), nullable=True),
        sa.Column("rxotcind", sa.String(length=1), nullable=True),
        sa.Column("mark", sa.String(length=10), nullable=True),
        sa.Column("calledinby", sa.String(length=50), nullable=True),
        sa.Column("quickcode", sa.String(length=10), nullable=True),
        sa.Column("tierset", sa.String(length=1), nullable=True),
        sa.Column("appeal", sa.String(length=3), nullable=True),
        sa.Column("denial", sa.String(length=2), nullable=True),
        sa.Column("timeframe", sa.String(length=2), nullable=True),
        sa.Column("reqreceived", sa.Date(), nullable=True),
        sa.Column("documentation", sa.Date(), nullable=True),
        sa.Column("reqapproved", sa.Date(), nullable=True),
        sa.Column("memnotified", sa.Date(), nullable=True),
        sa.Column("daysold", sa.Numeric(), nullable=True),
        sa.Column("maxscripts", sa.Numeric(), nullable=True),
        sa.Column("reportingndc", sa.String(length=11), nullable=True),
        sa.Column("reportingphys", sa.String(length=15), nullable=True),
        sa.Column("mincouponvalue", sa.Numeric(), nullable=True),
        sa.Column("maxcouponvalue", sa.Numeric(), nullable=True),
        sa.Column("maxdawamt", sa.Numeric(), nullable=True),
        sa.Column("mincouponcopay", sa.Numeric(), nullable=True),
        sa.Column("sdc", sa.String(length=20), nullable=True),
        sa.Column("eocid", sa.String(length=11), nullable=True),
        sa.Column("dawpercent", sa.Numeric(), nullable=True),
        sa.Column("mischandler", sa.String(length=20), nullable=True),
        sa.Column("mpatype", sa.String(length=25), nullable=True),
        sa.Column("bitflags2", sa.Numeric(), nullable=True),
        sa.Column("ignoremischandler", sa.String(length=20), nullable=True),
        sa.Column("ignorepm2", sa.String(length=55), nullable=True),
        sa.Column("ignorepm3", sa.String(length=55), nullable=True),
        sa.Column("manualgenname", sa.String(length=70), nullable=True),
        sa.Column("maxmpascripts", sa.Numeric(), nullable=True),
        sa.Column("subgroup", sa.String(length=20), nullable=True),
        sa.Column("batchbitflags", sa.Numeric(), nullable=True),
        sa.Column("origgroupnum", sa.String(length=20), nullable=True),
        sa.Column("couponds", sa.Numeric(), nullable=True),
        sa.Column("couponuses", sa.Numeric(), nullable=True),
        sa.Column("maxamtunit", sa.Numeric(), nullable=True),
        sa.Column("totalqtypercoupon", sa.Numeric(), nullable=True),
        sa.Column("hicn", sa.String(length=20), nullable=True),
        sa.Column("origcontractid", sa.String(length=20), nullable=True),
        sa.Column("origpbp", sa.String(length=4), nullable=True),
        sa.Column("setclaimtag", sa.String(length=200), nullable=True),
        sa.Column("compoundcode", sa.Numeric(), nullable=True),
        sa.Column("reportingcui", sa.String(length=7), nullable=True),
        sa.Column("diagnosis", sa.String(length=100), nullable=True),
        sa.Column("ingstrength", sa.Numeric(), nullable=True),
        sa.Column("bitflags3", sa.Numeric(precision=38, scale=0), nullable=True),
        sa.Column("minscriptqty", sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column("minscriptdays", sa.Numeric(precision=3, scale=0), nullable=True),
        sa.Column("ignoreduringr", sa.String(length=24), nullable=True),
        sa.Column("basic_review_date", sa.Date(), nullable=True),
        sa.Column("standard_review_date", sa.Date(), nullable=True),
        sa.Column("complex_review_date", sa.Date(), nullable=True),
        sa.Column("rereview_date", sa.Date(), nullable=True),
        sa.Column("no_charge_date", sa.Date(), nullable=True),
        sa.Column("internal_appeal_date", sa.Date(), nullable=True),
        sa.Column("brand", sa.String(length=4), nullable=True),
        sa.Column("reportingtype", sa.String(length=15), nullable=True),
        sa.Column("proffeehandler", sa.String(length=20), nullable=True),
        sa.Column("displimitshandler", sa.String(length=20), nullable=True),
        sa.Column("seconddiagnosis", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_prior_auths_authnum"), "prior_auths", ["authnum"], unique=True
    )
    op.create_index(
        "ix_prior_auths_subscribernum_groupnum",
        "prior_auths",
        ["subscribernum", "groupnum"],
    )
    op.create_index("ix_prior_auths_ndc", "prior_auths", ["ndc"])
    op.create_index("ix_prior_auths_gpi", "prior_auths", ["gpi"])
    op.create_index(
        "ix_prior_auths_effdate_termdate", "prior_auths", ["effdate", "termdate"]
    )


def downgrade() -> None:
    op.drop_index("ix_prior_auths_effdate_termdate", table_name="prior_auths")
    op.drop_index("ix_prior_auths_gpi", table_name="prior_auths")
    op.drop_index("ix_prior_auths_ndc", table_name="prior_auths")
    op.drop_index("ix_prior_auths_subscribernum_groupnum", table_name="prior_auths")
    op.drop_index(op.f("ix_prior_auths_authnum"), table_name="prior_auths")
    op.drop_table("prior_auths")
