"""add masterdrug table

Revision ID: c9f1a2b3d4e5
Revises: a5b6c7d8e9f0
Create Date: 2026-08-20 00:00:00.000000

Mirrors the legacy SQLMGR.MASTERDRUG feed table. The existing "drugs" table
is left untouched.

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9f1a2b3d4e5"
down_revision: Union[str, Sequence[str], None] = "a5b6c7d8e9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "masterdrug",
        sa.Column("ndcupchri", sa.String(length=11), nullable=False),
        sa.Column("idtype", sa.String(length=1), nullable=True),
        sa.Column("trancode", sa.String(length=1), nullable=True),
        sa.Column("seqcode", sa.String(length=7), nullable=True),
        sa.Column("labelercode", sa.String(length=5), nullable=True),
        sa.Column("genidtype", sa.String(length=1), nullable=True),
        sa.Column("genidnumber", sa.String(length=9), nullable=True),
        sa.Column("deaclasscode", sa.String(length=5), nullable=True),
        sa.Column("therclasscode", sa.String(length=6), nullable=True),
        sa.Column("statusflag", sa.String(length=1), nullable=True),
        sa.Column("localsystem", sa.String(length=1), nullable=True),
        sa.Column("teecode", sa.String(length=2), nullable=True),
        sa.Column("fmtid", sa.String(length=13), nullable=True),
        sa.Column("rxotcind", sa.String(length=1), nullable=True),
        sa.Column("tparestrictioncode", sa.String(length=1), nullable=True),
        sa.Column("maintdrugcode", sa.String(length=1), nullable=True),
        sa.Column("dispunitcode", sa.String(length=1), nullable=True),
        sa.Column("unitdose", sa.String(length=1), nullable=True),
        sa.Column("rtofadmin", sa.String(length=2), nullable=True),
        sa.Column("formtype", sa.String(length=1), nullable=True),
        sa.Column("numsystem", sa.String(length=1), nullable=True),
        sa.Column("secondidtype", sa.String(length=1), nullable=True),
        sa.Column("secondidnum", sa.String(length=10), nullable=True),
        sa.Column("multisource", sa.String(length=1), nullable=True),
        sa.Column("brandcode", sa.String(length=1), nullable=True),
        sa.Column("reimburseind", sa.String(length=1), nullable=True),
        sa.Column("intextcode", sa.String(length=1), nullable=True),
        sa.Column("singlecombocode", sa.String(length=1), nullable=True),
        sa.Column("storagecondition", sa.String(length=1), nullable=True),
        sa.Column("stabilitycode", sa.String(length=1), nullable=True),
        sa.Column("alastchange", sa.DateTime(), nullable=True),
        sa.Column("gpi", sa.String(length=14), nullable=True),
        sa.Column("gpigenname", sa.String(length=60), nullable=True),
        sa.Column("glastchange", sa.DateTime(), nullable=True),
        sa.Column("manuname", sa.String(length=30), nullable=True),
        sa.Column("manuabbrev", sa.String(length=10), nullable=True),
        sa.Column("proddescabbrev", sa.String(length=25), nullable=True),
        sa.Column("drugnamecode", sa.String(length=6), nullable=True),
        sa.Column("gppc", sa.String(length=8), nullable=True),
        sa.Column("jlastchange", sa.DateTime(), nullable=True),
        sa.Column("strength", sa.Numeric(), nullable=True),
        sa.Column("strengthuom", sa.String(length=12), nullable=True),
        sa.Column("dosageform", sa.String(length=4), nullable=True),
        sa.Column("packagesize", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("pkgsizeuom", sa.String(length=2), nullable=True),
        sa.Column("pkgqty", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("repackcode", sa.String(length=1), nullable=True),
        sa.Column("totalpkgqty", sa.Numeric(), nullable=True),
        sa.Column("desi", sa.String(length=1), nullable=True),
        sa.Column("pkgdesc", sa.String(length=10), nullable=True),
        sa.Column("nsns", sa.String(length=2), nullable=True),
        sa.Column("nlns", sa.String(length=2), nullable=True),
        sa.Column("innerpack", sa.String(length=1), nullable=True),
        sa.Column("clinicpack", sa.String(length=1), nullable=True),
        sa.Column("llastchange", sa.DateTime(), nullable=True),
        sa.Column("awpindcode", sa.String(length=1), nullable=True),
        sa.Column("awppkgprice", sa.Numeric(), nullable=True),
        sa.Column("awpunitprice", sa.Numeric(), nullable=True),
        sa.Column("awpeffdate", sa.Date(), nullable=True),
        sa.Column("awp1stpkgprice", sa.Numeric(), nullable=True),
        sa.Column("awp1stunitprice", sa.Numeric(), nullable=True),
        sa.Column("awp1steffdate", sa.Date(), nullable=True),
        sa.Column("awp2ndpkgprice", sa.Numeric(), nullable=True),
        sa.Column("awp2ndunitprice", sa.Numeric(), nullable=True),
        sa.Column("awp2ndeffdate", sa.Date(), nullable=True),
        sa.Column("wacunitprice", sa.Numeric(), nullable=True),
        sa.Column("rlastchange", sa.DateTime(), nullable=True),
        sa.Column("dppkgprice", sa.Numeric(), nullable=True),
        sa.Column("dpunitprice", sa.Numeric(), nullable=True),
        sa.Column("dpeffdate", sa.Date(), nullable=True),
        sa.Column("dp1stpkgprice", sa.Numeric(), nullable=True),
        sa.Column("dp1stunitprice", sa.Numeric(), nullable=True),
        sa.Column("dp1steffdate", sa.Date(), nullable=True),
        sa.Column("dp2ndpkgprice", sa.Numeric(), nullable=True),
        sa.Column("dp2ndunitprice", sa.Numeric(), nullable=True),
        sa.Column("dp2ndeffdate", sa.Date(), nullable=True),
        sa.Column("slastchange", sa.DateTime(), nullable=True),
        sa.Column("hcfaprice", sa.Numeric(), nullable=True),
        sa.Column("hcfaeffdate", sa.Date(), nullable=True),
        sa.Column("hcfa1stprice", sa.Numeric(), nullable=True),
        sa.Column("hcfa1steffdate", sa.Date(), nullable=True),
        sa.Column("hcfa2ndprice", sa.Numeric(), nullable=True),
        sa.Column("hcfa2ndeffdate", sa.Date(), nullable=True),
        sa.Column("tlastchange", sa.DateTime(), nullable=True),
        sa.Column("mddbmony", sa.String(length=1), nullable=True),
        sa.Column("mddbmaint", sa.String(length=1), nullable=True),
        sa.Column("extradrug", sa.String(length=1), nullable=True),
        sa.Column("newndc", sa.String(length=11), nullable=True),
        sa.Column("clastchange", sa.DateTime(), nullable=True),
        sa.Column("lswlastchange", sa.DateTime(), nullable=True),
        sa.Column("prodname", sa.String(length=25), nullable=True),
        sa.Column("gcn", sa.String(length=6), nullable=True),
        sa.Column("gc3", sa.String(length=4), nullable=True),
        sa.Column("cl", sa.String(length=2), nullable=True),
        sa.Column("inactivedate", sa.Date(), nullable=True),
        sa.Column("mlastchange", sa.DateTime(), nullable=True),
        sa.Column("waceffdate", sa.Date(), nullable=True),
        sa.Column("wac1stunitprice", sa.Numeric(), nullable=True),
        sa.Column("wac1steffdate", sa.Date(), nullable=True),
        sa.Column("wac2ndunitprice", sa.Numeric(), nullable=True),
        sa.Column("wac2ndeffdate", sa.Date(), nullable=True),
        sa.Column("qlastchange", sa.DateTime(), nullable=True),
        sa.Column("elastchange", sa.DateTime(), nullable=True),
        sa.Column("manualupdate", sa.DateTime(), nullable=True),
        sa.Column("mddbawpeffdate", sa.Date(), nullable=True),
        sa.Column("mddbawppkgprice", sa.Numeric(), nullable=True),
        sa.Column("mddbawpunitprice", sa.Numeric(), nullable=True),
        sa.Column("mddbawp1steffdate", sa.Date(), nullable=True),
        sa.Column("mddbawp1stpkgprice", sa.Numeric(), nullable=True),
        sa.Column("mddbawp1stunitprice", sa.Numeric(), nullable=True),
        sa.Column("mddbawp2ndeffdate", sa.Date(), nullable=True),
        sa.Column("mddbawp2ndpkgprice", sa.Numeric(), nullable=True),
        sa.Column("mddbawp2ndunitprice", sa.Numeric(), nullable=True),
        sa.Column("awplastchange", sa.DateTime(), nullable=True),
        sa.Column("gsn", sa.String(length=6), nullable=True),
        sa.Column("hicl", sa.String(length=6), nullable=True),
        sa.Column("hic3", sa.String(length=3), nullable=True),
        sa.Column("tc", sa.String(length=2), nullable=True),
        sa.Column("dcc", sa.String(length=1), nullable=True),
        sa.Column("dp3rdeffdate", sa.Date(), nullable=True),
        sa.Column("dp3rdpkgprice", sa.Numeric(), nullable=True),
        sa.Column("dp3rdunitprice", sa.Numeric(), nullable=True),
        sa.Column("dp4theffdate", sa.Date(), nullable=True),
        sa.Column("dp4thpkgprice", sa.Numeric(), nullable=True),
        sa.Column("dp4thunitprice", sa.Numeric(), nullable=True),
        sa.Column("mddbawp3rdeffdate", sa.Date(), nullable=True),
        sa.Column("mddbawp3rdpkgprice", sa.Numeric(), nullable=True),
        sa.Column("mddbawp3rdunitprice", sa.Numeric(), nullable=True),
        sa.Column("mddbawp4theffdate", sa.Date(), nullable=True),
        sa.Column("mddbawp4thpkgprice", sa.Numeric(), nullable=True),
        sa.Column("mddbawp4thunitprice", sa.Numeric(), nullable=True),
        sa.Column("awp3rdeffdate", sa.Date(), nullable=True),
        sa.Column("awp3rdpkgprice", sa.Numeric(), nullable=True),
        sa.Column("awp3rdunitprice", sa.Numeric(), nullable=True),
        sa.Column("awp4theffdate", sa.Date(), nullable=True),
        sa.Column("awp4thpkgprice", sa.Numeric(), nullable=True),
        sa.Column("awp4thunitprice", sa.Numeric(), nullable=True),
        sa.Column("wac3rdunitprice", sa.Numeric(), nullable=True),
        sa.Column("wac3rdeffdate", sa.Date(), nullable=True),
        sa.Column("wac4thunitprice", sa.Numeric(), nullable=True),
        sa.Column("wac4theffdate", sa.Date(), nullable=True),
        sa.Column("mddbunitdose", sa.String(length=1), nullable=True),
        sa.Column("dollarrankcode", sa.String(length=1), nullable=True),
        sa.Column("rxrankcode", sa.String(length=1), nullable=True),
        sa.Column("productnameext", sa.String(length=35), nullable=True),
        sa.Column("allergypatterncode", sa.String(length=4), nullable=True),
        sa.Column("ppgindicatorcode", sa.String(length=1), nullable=True),
        sa.Column("hfpgindicatorcode", sa.String(length=1), nullable=True),
        sa.Column("labelertypecode", sa.String(length=1), nullable=True),
        sa.Column("pricingspreadcode", sa.String(length=1), nullable=True),
        sa.Column("limiteddistcode", sa.String(length=2), nullable=True),
        sa.Column("extahfstherclasscode", sa.String(length=8), nullable=True),
        sa.Column("wacpkgprice", sa.Numeric(), nullable=True),
        sa.Column("wac1stpkgprice", sa.Numeric(), nullable=True),
        sa.Column("wac2ndpkgprice", sa.Numeric(), nullable=True),
        sa.Column("wac3rdpkgprice", sa.Numeric(), nullable=True),
        sa.Column("wac4thpkgprice", sa.Numeric(), nullable=True),
        sa.Column("mddbfile", sa.String(length=30), nullable=True),
        sa.Column("mddbdate", sa.DateTime(), nullable=True),
        sa.Column("noawpupdate", sa.String(length=1), nullable=True),
        sa.Column("manualadd", sa.String(length=1), nullable=True),
        sa.Column("mddbgpi", sa.String(length=14), nullable=True),
        sa.Column("mddbgpigenname", sa.String(length=60), nullable=True),
        sa.Column("mddbgpifile", sa.String(length=30), nullable=True),
        sa.Column("mddbgpistatus", sa.String(length=1), nullable=True),
        sa.Column("gpilastchange", sa.DateTime(), nullable=True),
        sa.Column("ndcaddfile", sa.String(length=30), nullable=True),
        sa.Column("ndcadddate", sa.DateTime(), nullable=True),
        sa.Column("prcmddbfile", sa.String(length=30), nullable=True),
        sa.Column("prcmddbdate", sa.DateTime(), nullable=True),
        sa.Column("datmddbfile", sa.String(length=30), nullable=True),
        sa.Column("datmddbdate", sa.DateTime(), nullable=True),
        sa.Column("mddbteecode", sa.String(length=2), nullable=True),
        sa.Column("ddid", sa.String(length=6), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_masterdrug_gpi"), "masterdrug", ["gpi"], unique=False)
    op.create_index(
        op.f("ix_masterdrug_gpigenname"), "masterdrug", ["gpigenname"], unique=False
    )
    op.create_index(
        op.f("ix_masterdrug_gsn_extradrug"),
        "masterdrug",
        ["gsn", "extradrug"],
        unique=False,
    )
    op.create_index(
        op.f("ix_masterdrug_manuname"), "masterdrug", ["manuname"], unique=False
    )
    op.create_index(
        op.f("ix_masterdrug_ndcupchri"), "masterdrug", ["ndcupchri"], unique=True
    )
    op.create_index(
        op.f("ix_masterdrug_proddescabbrev"),
        "masterdrug",
        ["proddescabbrev"],
        unique=False,
    )
    op.create_index(
        op.f("ix_masterdrug_prodname"), "masterdrug", ["prodname"], unique=False
    )
    op.create_index(
        op.f("ix_masterdrug_therclasscode"),
        "masterdrug",
        ["therclasscode"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_masterdrug_therclasscode"), table_name="masterdrug")
    op.drop_index(op.f("ix_masterdrug_prodname"), table_name="masterdrug")
    op.drop_index(op.f("ix_masterdrug_proddescabbrev"), table_name="masterdrug")
    op.drop_index(op.f("ix_masterdrug_ndcupchri"), table_name="masterdrug")
    op.drop_index(op.f("ix_masterdrug_manuname"), table_name="masterdrug")
    op.drop_index(op.f("ix_masterdrug_gsn_extradrug"), table_name="masterdrug")
    op.drop_index(op.f("ix_masterdrug_gpigenname"), table_name="masterdrug")
    op.drop_index(op.f("ix_masterdrug_gpi"), table_name="masterdrug")
    op.drop_table("masterdrug")
