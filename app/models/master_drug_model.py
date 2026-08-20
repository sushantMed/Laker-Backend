from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.gpi_desc_model import GpiDescModel


class MasterDrugModel(Base):
    """Mirror of the legacy SQLMGR.MASTERDRUG table (the MediSpan/FDB feed).

    Distinct from DrugModel ("drugs"), which stays as-is: that table is the
    application's own curated drug list, this one is the raw vendor load with
    every pricing tier and last-change marker the feed carries.

    Oracle DATE columns are split by how the feed uses them: the *lastchange /
    load-file markers keep their time component (DateTime), the pricing
    effective dates and inactivedate are day-granular (Date).

    Only the single-column legacy indexes are reproduced. The wide covering
    indexes on the Oracle side (XRULE_FDB_HELPER_IDX, DRUG_PROFILE_IDX,
    MD_ACTIVECLM_IDX, MD_HIST_PROF_IDX) exist for specific prod query plans
    over a multi-million-row table and are not carried over here.
    """

    __tablename__ = "masterdrug"

    __table_args__ = (
        Index("ix_masterdrug_gpi", "gpi"),
        Index("ix_masterdrug_gpigenname", "gpigenname"),
        Index("ix_masterdrug_prodname", "prodname"),
        Index("ix_masterdrug_proddescabbrev", "proddescabbrev"),
        Index("ix_masterdrug_manuname", "manuname"),
        Index("ix_masterdrug_therclasscode", "therclasscode"),
        # MD_GSN_XREF_IDX is function-based on Oracle (TO_NUMBER(GSN)); GSN is
        # a zero-padded numeric string, so a plain index serves the same lookup.
        Index("ix_masterdrug_gsn_extradrug", "gsn", "extradrug"),
    )

    ndcupchri: Mapped[str] = mapped_column(
        String(11), unique=True, index=True, nullable=False
    )
    idtype: Mapped[str | None] = mapped_column(String(1), nullable=True)
    trancode: Mapped[str | None] = mapped_column(String(1), nullable=True)
    seqcode: Mapped[str | None] = mapped_column(String(7), nullable=True)
    labelercode: Mapped[str | None] = mapped_column(String(5), nullable=True)
    genidtype: Mapped[str | None] = mapped_column(String(1), nullable=True)
    genidnumber: Mapped[str | None] = mapped_column(String(9), nullable=True)
    deaclasscode: Mapped[str | None] = mapped_column(String(5), nullable=True)
    therclasscode: Mapped[str | None] = mapped_column(String(6), nullable=True)
    statusflag: Mapped[str | None] = mapped_column(String(1), nullable=True)
    localsystem: Mapped[str | None] = mapped_column(String(1), nullable=True)
    teecode: Mapped[str | None] = mapped_column(String(2), nullable=True)
    fmtid: Mapped[str | None] = mapped_column(String(13), nullable=True)
    rxotcind: Mapped[str | None] = mapped_column(String(1), nullable=True)
    tparestrictioncode: Mapped[str | None] = mapped_column(String(1), nullable=True)
    maintdrugcode: Mapped[str | None] = mapped_column(String(1), nullable=True)
    dispunitcode: Mapped[str | None] = mapped_column(String(1), nullable=True)
    unitdose: Mapped[str | None] = mapped_column(String(1), nullable=True)
    rtofadmin: Mapped[str | None] = mapped_column(String(2), nullable=True)
    formtype: Mapped[str | None] = mapped_column(String(1), nullable=True)
    numsystem: Mapped[str | None] = mapped_column(String(1), nullable=True)
    secondidtype: Mapped[str | None] = mapped_column(String(1), nullable=True)
    secondidnum: Mapped[str | None] = mapped_column(String(10), nullable=True)
    multisource: Mapped[str | None] = mapped_column(String(1), nullable=True)
    brandcode: Mapped[str | None] = mapped_column(String(1), nullable=True)
    reimburseind: Mapped[str | None] = mapped_column(String(1), nullable=True)
    intextcode: Mapped[str | None] = mapped_column(String(1), nullable=True)
    singlecombocode: Mapped[str | None] = mapped_column(String(1), nullable=True)
    storagecondition: Mapped[str | None] = mapped_column(String(1), nullable=True)
    stabilitycode: Mapped[str | None] = mapped_column(String(1), nullable=True)
    alastchange: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    gpi: Mapped[str | None] = mapped_column(String(14), nullable=True)
    gpigenname: Mapped[str | None] = mapped_column(String(60), nullable=True)
    glastchange: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    manuname: Mapped[str | None] = mapped_column(String(30), nullable=True)
    manuabbrev: Mapped[str | None] = mapped_column(String(10), nullable=True)
    proddescabbrev: Mapped[str | None] = mapped_column(String(25), nullable=True)
    drugnamecode: Mapped[str | None] = mapped_column(String(6), nullable=True)
    gppc: Mapped[str | None] = mapped_column(String(8), nullable=True)
    jlastchange: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    strength: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    strengthuom: Mapped[str | None] = mapped_column(String(12), nullable=True)
    dosageform: Mapped[str | None] = mapped_column(String(4), nullable=True)
    packagesize: Mapped[Decimal | None] = mapped_column(Numeric(8, 3), nullable=True)
    pkgsizeuom: Mapped[str | None] = mapped_column(String(2), nullable=True)
    pkgqty: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    repackcode: Mapped[str | None] = mapped_column(String(1), nullable=True)
    totalpkgqty: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    desi: Mapped[str | None] = mapped_column(String(1), nullable=True)
    pkgdesc: Mapped[str | None] = mapped_column(String(10), nullable=True)
    nsns: Mapped[str | None] = mapped_column(String(2), nullable=True)
    nlns: Mapped[str | None] = mapped_column(String(2), nullable=True)
    innerpack: Mapped[str | None] = mapped_column(String(1), nullable=True)
    clinicpack: Mapped[str | None] = mapped_column(String(1), nullable=True)
    llastchange: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    awpindcode: Mapped[str | None] = mapped_column(String(1), nullable=True)
    awppkgprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    awpunitprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    awpeffdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    awp1stpkgprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    awp1stunitprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    awp1steffdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    awp2ndpkgprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    awp2ndunitprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    awp2ndeffdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    wacunitprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    rlastchange: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    dppkgprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    dpunitprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    dpeffdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    dp1stpkgprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    dp1stunitprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    dp1steffdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    dp2ndpkgprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    dp2ndunitprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    dp2ndeffdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    slastchange: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    hcfaprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    hcfaeffdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    hcfa1stprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    hcfa1steffdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    hcfa2ndprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    hcfa2ndeffdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    tlastchange: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    mddbmony: Mapped[str | None] = mapped_column(String(1), nullable=True)
    mddbmaint: Mapped[str | None] = mapped_column(String(1), nullable=True)
    extradrug: Mapped[str | None] = mapped_column(String(1), nullable=True)
    newndc: Mapped[str | None] = mapped_column(String(11), nullable=True)
    clastchange: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    lswlastchange: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    prodname: Mapped[str | None] = mapped_column(String(25), nullable=True)
    gcn: Mapped[str | None] = mapped_column(String(6), nullable=True)
    gc3: Mapped[str | None] = mapped_column(String(4), nullable=True)
    cl: Mapped[str | None] = mapped_column(String(2), nullable=True)
    inactivedate: Mapped[date | None] = mapped_column(Date, nullable=True)
    mlastchange: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    waceffdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    wac1stunitprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    wac1steffdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    wac2ndunitprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    wac2ndeffdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    qlastchange: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    elastchange: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    manualupdate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    mddbawpeffdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    mddbawppkgprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    mddbawpunitprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    mddbawp1steffdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    mddbawp1stpkgprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    mddbawp1stunitprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    mddbawp2ndeffdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    mddbawp2ndpkgprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    mddbawp2ndunitprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    awplastchange: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    gsn: Mapped[str | None] = mapped_column(String(6), nullable=True)
    hicl: Mapped[str | None] = mapped_column(String(6), nullable=True)
    hic3: Mapped[str | None] = mapped_column(String(3), nullable=True)
    tc: Mapped[str | None] = mapped_column(String(2), nullable=True)
    dcc: Mapped[str | None] = mapped_column(String(1), nullable=True)
    dp3rdeffdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    dp3rdpkgprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    dp3rdunitprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    dp4theffdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    dp4thpkgprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    dp4thunitprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    mddbawp3rdeffdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    mddbawp3rdpkgprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    mddbawp3rdunitprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    mddbawp4theffdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    mddbawp4thpkgprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    mddbawp4thunitprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    awp3rdeffdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    awp3rdpkgprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    awp3rdunitprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    awp4theffdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    awp4thpkgprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    awp4thunitprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    wac3rdunitprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    wac3rdeffdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    wac4thunitprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    wac4theffdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    mddbunitdose: Mapped[str | None] = mapped_column(String(1), nullable=True)
    dollarrankcode: Mapped[str | None] = mapped_column(String(1), nullable=True)
    rxrankcode: Mapped[str | None] = mapped_column(String(1), nullable=True)
    productnameext: Mapped[str | None] = mapped_column(String(35), nullable=True)
    allergypatterncode: Mapped[str | None] = mapped_column(String(4), nullable=True)
    ppgindicatorcode: Mapped[str | None] = mapped_column(String(1), nullable=True)
    hfpgindicatorcode: Mapped[str | None] = mapped_column(String(1), nullable=True)
    labelertypecode: Mapped[str | None] = mapped_column(String(1), nullable=True)
    pricingspreadcode: Mapped[str | None] = mapped_column(String(1), nullable=True)
    limiteddistcode: Mapped[str | None] = mapped_column(String(2), nullable=True)
    extahfstherclasscode: Mapped[str | None] = mapped_column(String(8), nullable=True)
    wacpkgprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    wac1stpkgprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    wac2ndpkgprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    wac3rdpkgprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    wac4thpkgprice: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    mddbfile: Mapped[str | None] = mapped_column(String(30), nullable=True)
    mddbdate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    noawpupdate: Mapped[str | None] = mapped_column(String(1), nullable=True)
    manualadd: Mapped[str | None] = mapped_column(String(1), nullable=True)
    mddbgpi: Mapped[str | None] = mapped_column(String(14), nullable=True)
    mddbgpigenname: Mapped[str | None] = mapped_column(String(60), nullable=True)
    mddbgpifile: Mapped[str | None] = mapped_column(String(30), nullable=True)
    mddbgpistatus: Mapped[str | None] = mapped_column(String(1), nullable=True)
    gpilastchange: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ndcaddfile: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ndcadddate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    prcmddbfile: Mapped[str | None] = mapped_column(String(30), nullable=True)
    prcmddbdate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    datmddbfile: Mapped[str | None] = mapped_column(String(30), nullable=True)
    datmddbdate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    mddbteecode: Mapped[str | None] = mapped_column(String(2), nullable=True)
    ddid: Mapped[str | None] = mapped_column(String(6), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    # Joined on the GPI value rather than a foreign key -- see GpiDescModel.
    # There is no matching link to GpiListModel: that table keys a *partial*
    # GPI as "G" + a prefix of unknown length, which no join condition can
    # express. GpiRepository resolves those.
    gpi_description: Mapped[GpiDescModel | None] = relationship(
        "GpiDescModel",
        primaryjoin="foreign(MasterDrugModel.gpi) == GpiDescModel.gpi",
        viewonly=True,
        lazy="noload",
    )
