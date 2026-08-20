from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, LookupBase
from app.utils.enums import CoverageType, Gender


class MemberModel(Base):
    __tablename__ = "members"

    # ── Primary key ──────────────────────────────────────────────────────────
    member_id: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )

    # ── Family linkage ───────────────────────────────────────────────────────
    # NULL means this member IS the subscriber (cardholder).
    subscriber_member_id: Mapped[str | None] = mapped_column(
        String(20),
        ForeignKey("members.member_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    # ── Name ─────────────────────────────────────────────────────────────────
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    mi: Mapped[str | None] = mapped_column(String(1), nullable=True)

    # ── Demographics ─────────────────────────────────────────────────────────
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[Gender | None] = mapped_column(SQLEnum(Gender), nullable=True)
    ssn: Mapped[str | None] = mapped_column(
        String(11), nullable=True
    )  # stored encrypted in prod

    # ── Contact ──────────────────────────────────────────────────────────────
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language_preference: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # ── Identifiers ──────────────────────────────────────────────────────────
    insured_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    person_code: Mapped[str] = mapped_column(String(5), nullable=False)
    family_position: Mapped[str | None] = mapped_column(String(5), nullable=True)
    rel_code: Mapped[str] = mapped_column(
        String(5), nullable=False
    )  # "01" / "02" / "03+"
    laker_pc: Mapped[str | None] = mapped_column(String(20), nullable=True)
    prev_card_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    cov_type: Mapped[CoverageType | None] = mapped_column(
        SQLEnum(CoverageType), nullable=True
    )

    # ── Eligibility (stored on Member, not a separate table) ─────────────────
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    # ── Plan FK ──────────────────────────────────────────────────────────────
    plan_id: Mapped[str | None] = mapped_column(
        String(20),
        ForeignKey("plans.plan_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    # ── Audit ────────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    plan: Mapped["PlanModel | None"] = relationship(  # noqa: F821
        "PlanModel", back_populates="members", lazy="joined"
    )
    address: Mapped["MemberAddressModel | None"] = relationship(  # noqa: F821
        "MemberAddressModel",
        back_populates="member",
        uselist=False,
        lazy="joined",
        cascade="all, delete-orphan",
    )
    # Self-referential: dependents of this cardholder
    dependents: Mapped[list["MemberModel"]] = relationship(
        "MemberModel",
        foreign_keys=[subscriber_member_id],
        back_populates="subscriber",
        lazy="noload",
    )
    subscriber: Mapped["MemberModel | None"] = relationship(
        "MemberModel",
        foreign_keys=[subscriber_member_id],
        back_populates="dependents",
        remote_side=[member_id],
        lazy="noload",
    )


class Subscriber(LookupBase):
    __tablename__ = "SUBSCRIBER"

    # --- Composite primary key ---
    subscribernum: Mapped[str] = mapped_column(
        "SUBSCRIBERNUM", String(45), primary_key=True
    )
    personcode: Mapped[str] = mapped_column("PERSONCODE", String(2), primary_key=True)
    clientcode: Mapped[str] = mapped_column("CLIENTCODE", String(10), primary_key=True)

    # --- Identity / demographics ---
    ssn: Mapped[str | None] = mapped_column("SSN", String(9))
    lastname: Mapped[str | None] = mapped_column("LASTNAME", String(25))
    firstname: Mapped[str | None] = mapped_column("FIRSTNAME", String(25))
    mi: Mapped[str | None] = mapped_column("MI", String(1))
    addr1: Mapped[str | None] = mapped_column("ADDR1", String(55))
    addr2: Mapped[str | None] = mapped_column("ADDR2", String(55))
    city: Mapped[str | None] = mapped_column("CITY", String(20))
    state: Mapped[str | None] = mapped_column("STATE", String(2))
    zip: Mapped[str | None] = mapped_column("ZIP", String(11))
    homephone: Mapped[str | None] = mapped_column("HOMEPHONE", String(10))
    workphone: Mapped[str | None] = mapped_column("WORKPHONE", String(10))
    dob: Mapped[datetime | None] = mapped_column("DOB", DateTime)
    termination: Mapped[datetime | None] = mapped_column("TERMINATION", DateTime)
    status: Mapped[str | None] = mapped_column("STATUS", String(1))
    gender: Mapped[str | None] = mapped_column("GENDER", String(1))
    carrier: Mapped[str | None] = mapped_column("CARRIER", String(10))
    location: Mapped[str | None] = mapped_column("LOCATION", String(10))
    updatets: Mapped[datetime | None] = mapped_column("UPDATETS", DateTime)
    dateentered: Mapped[datetime | None] = mapped_column("DATEENTERED", DateTime)
    carddate: Mapped[datetime | None] = mapped_column("CARDDATE", DateTime)
    numcards: Mapped[int | None] = mapped_column("NUMCARDS", Integer)
    testonly: Mapped[int | None] = mapped_column("TESTONLY", Integer)

    # --- Injury / claim ---
    injdate: Mapped[datetime | None] = mapped_column("INJDATE", DateTime)
    injtype: Mapped[str | None] = mapped_column("INJTYPE", String(30))
    broker1: Mapped[str | None] = mapped_column("BROKER1", String(10))
    broker2: Mapped[str | None] = mapped_column("BROKER2", String(10))
    employername: Mapped[str | None] = mapped_column("EMPLOYERNAME", String(40))
    employeraddr1: Mapped[str | None] = mapped_column("EMPLOYERADDR1", String(40))
    employeraddr2: Mapped[str | None] = mapped_column("EMPLOYERADDR2", String(40))
    employercity: Mapped[str | None] = mapped_column("EMPLOYERCITY", String(20))
    employerstate: Mapped[str | None] = mapped_column("EMPLOYERSTATE", String(2))
    employerzip: Mapped[str | None] = mapped_column("EMPLOYERZIP", String(11))
    adjuster: Mapped[str | None] = mapped_column("ADJUSTER", String(25))
    venuestate: Mapped[str | None] = mapped_column("VENUESTATE", String(2))
    injcause: Mapped[str | None] = mapped_column("INJCAUSE", String(100))
    claimid: Mapped[str | None] = mapped_column("CLAIMID", String(30))

    # --- Payment / card ---
    copaybankamt: Mapped[Decimal | None] = mapped_column("COPAYBANKAMT", Numeric(12, 2))
    copaybanktype: Mapped[str | None] = mapped_column("COPAYBANKTYPE", String(10))
    chargecardnum: Mapped[str | None] = mapped_column("CHARGECARDNUM", String(20))
    chargecardexp: Mapped[str | None] = mapped_column("CHARGECARDEXP", String(8))
    chargecardname: Mapped[str | None] = mapped_column("CHARGECARDNAME", String(25))
    emailaddress: Mapped[str | None] = mapped_column("EMAILADDRESS", String(50))
    transitnum: Mapped[str | None] = mapped_column("TRANSITNUM", String(20))
    accountnum: Mapped[str | None] = mapped_column("ACCOUNTNUM", String(20))
    cardstatus: Mapped[str | None] = mapped_column("CARDSTATUS", String(2))
    cardstatusdate: Mapped[datetime | None] = mapped_column("CARDSTATUSDATE", DateTime)
    pcp: Mapped[str | None] = mapped_column("PCP", String(100))
    flex2: Mapped[str | None] = mapped_column("FLEX2", String(10))
    flex3: Mapped[str | None] = mapped_column("FLEX3", String(10))
    empcd: Mapped[str | None] = mapped_column("EMPCD", String(2))
    noupdate: Mapped[str | None] = mapped_column("NOUPDATE", String(1))
    addedby: Mapped[str | None] = mapped_column("ADDEDBY", String(30))
    mbrsince: Mapped[datetime | None] = mapped_column("MBRSINCE", DateTime)

    # --- Generic string slots (source system flex fields) ---
    str1_20: Mapped[str | None] = mapped_column("STR1_20", String(20))
    str2_20: Mapped[str | None] = mapped_column("STR2_20", String(20))
    str1_04: Mapped[str | None] = mapped_column("STR1_04", String(4))
    str1_15: Mapped[str | None] = mapped_column("STR1_15", String(15))
    str2_04: Mapped[str | None] = mapped_column("STR2_04", String(4))
    str2_15: Mapped[str | None] = mapped_column("STR2_15", String(15))
    relcode: Mapped[str | None] = mapped_column("RELCODE", String(2))
    eligoverride: Mapped[str | None] = mapped_column("ELIGOVERRIDE", String(2))
    str3_20: Mapped[str | None] = mapped_column("STR3_20", String(20))
    str1_01: Mapped[str | None] = mapped_column("STR1_01", String(1))
    str2_01: Mapped[str | None] = mapped_column("STR2_01", String(1))
    str1_05: Mapped[str | None] = mapped_column("STR1_05", String(5))
    str1_10: Mapped[str | None] = mapped_column("STR1_10", String(10))
    flex1: Mapped[str | None] = mapped_column("FLEX1", String(10))
    str1_02: Mapped[str | None] = mapped_column("STR1_02", String(2))

    # --- Card / enrollment ---
    previouscardid: Mapped[str | None] = mapped_column("PREVIOUSCARDID", String(45))
    altcardid: Mapped[str | None] = mapped_column("ALTCARDID", String(45))
    enrolltype: Mapped[str | None] = mapped_column("ENROLLTYPE", String(3))
    enrollnabp: Mapped[str | None] = mapped_column("ENROLLNABP", String(12))
    source: Mapped[str | None] = mapped_column("SOURCE", String(10))
    authby: Mapped[str | None] = mapped_column("AUTHBY", String(50))
    nonhippaid: Mapped[str | None] = mapped_column("NONHIPPAID", String(18))
    mfname: Mapped[str | None] = mapped_column("MFNAME", String(20))
    cardprintdate: Mapped[datetime | None] = mapped_column("CARDPRINTDATE", DateTime)

    # --- PCP / pharmacy ---
    pcpphone: Mapped[str | None] = mapped_column("PCPPHONE", String(15))
    legalrep: Mapped[str | None] = mapped_column("LEGALREP", String(1))
    custact: Mapped[str | None] = mapped_column("CUSTACT", String(1))
    activationdate: Mapped[datetime | None] = mapped_column("ACTIVATIONDATE", DateTime)
    primarypharm: Mapped[str | None] = mapped_column("PRIMARYPHARM", String(50))
    pripharmphone: Mapped[str | None] = mapped_column("PRIPHARMPHONE", String(10))
    pripharmfax: Mapped[str | None] = mapped_column("PRIPHARMFAX", String(10))
    bookletdate: Mapped[datetime | None] = mapped_column("BOOKLETDATE", DateTime)
    bookletprintdate: Mapped[datetime | None] = mapped_column(
        "BOOKLETPRINTDATE", DateTime
    )
    country: Mapped[str | None] = mapped_column("COUNTRY", String(75))
    str1_50: Mapped[str | None] = mapped_column("STR1_50", String(50))
    employerphone: Mapped[str | None] = mapped_column("EMPLOYERPHONE", String(10))
    employerfax: Mapped[str | None] = mapped_column("EMPLOYERFAX", String(10))
    adjusterphone: Mapped[str | None] = mapped_column("ADJUSTERPHONE", String(10))
    adjusterfax: Mapped[str | None] = mapped_column("ADJUSTERFAX", String(10))
    bitflags: Mapped[int | None] = mapped_column("BITFLAGS", Integer)
    exteligsnext: Mapped[datetime | None] = mapped_column("EXTELIGNEXT", DateTime)
    exteliglast: Mapped[datetime | None] = mapped_column("EXTELIGLAST", DateTime)
    facility: Mapped[str | None] = mapped_column("FACILITY", String(50))
    pcpfax: Mapped[str | None] = mapped_column("PCPFAX", String(10))
    adjusteremail: Mapped[str | None] = mapped_column("ADJUSTEREMAIL", String(50))

    # --- Mailing address ---
    mailaddr1: Mapped[str | None] = mapped_column("MAILADDR1", String(50))
    mailaddr2: Mapped[str | None] = mapped_column("MAILADDR2", String(50))
    mailcity: Mapped[str | None] = mapped_column("MAILCITY", String(20))
    mailstate: Mapped[str | None] = mapped_column("MAILSTATE", String(2))
    mailzip: Mapped[str | None] = mapped_column("MAILZIP", String(11))
    cardapc: Mapped[str | None] = mapped_column("CARDAPC", String(2))
    cardbpc: Mapped[str | None] = mapped_column("CARDBPC", String(2))
    pcpid: Mapped[str | None] = mapped_column("PCPID", String(50))
    pcpgroup: Mapped[str | None] = mapped_column("PCPGROUP", String(100))
    ethnicity: Mapped[str | None] = mapped_column("ETHNICITY", String(2))
    race: Mapped[str | None] = mapped_column("RACE", String(2))

    # --- External identifiers ---
    issuerassignedmemid: Mapped[str | None] = mapped_column(
        "ISSUERASSIGNEDMEMID", String(45)
    )
    issuerassignedsubid: Mapped[str | None] = mapped_column(
        "ISSUERASSIGNEDSUBID", String(20)
    )
    priorinscarrierid: Mapped[str | None] = mapped_column(
        "PRIORINSCARRIERID", String(20)
    )
    lastpremiumpaiddate: Mapped[datetime | None] = mapped_column(
        "LASTPREMIUMPAIDDATE", DateTime
    )
    relationshipdesc: Mapped[str | None] = mapped_column("RELATIONSHIPDESC", String(45))
    mailfirstname: Mapped[str | None] = mapped_column("MAILFIRSTNAME", String(25))
    maillastname: Mapped[str | None] = mapped_column("MAILLASTNAME", String(25))
    mailprimaryphone: Mapped[str | None] = mapped_column("MAILPRIMARYPHONE", String(12))
    mailsecondaryphone: Mapped[str | None] = mapped_column(
        "MAILSECONDARYPHONE", String(12)
    )
    casemanager: Mapped[str | None] = mapped_column("CASEMANAGER", String(75))
    adjusterext: Mapped[str | None] = mapped_column("ADJUSTEREXT", String(10))

    # --- Workers' comp / group plan ---
    mprwc1: Mapped[str | None] = mapped_column("MPRWC1", String(2))
    mprwc2: Mapped[str | None] = mapped_column("MPRWC2", String(2))
    mprwc3: Mapped[str | None] = mapped_column("MPRWC3", String(2))
    gpenterdate: Mapped[datetime | None] = mapped_column("GPENTERDATE", DateTime)
    gpperiodseg: Mapped[str | None] = mapped_column("GPPERIODSEG", String(2))
    str3_01: Mapped[str | None] = mapped_column("STR3_01", String(1))
    str2_50: Mapped[str | None] = mapped_column("STR2_50", String(50))
    str3_50: Mapped[str | None] = mapped_column("STR3_50", String(50))
    langspoken: Mapped[str | None] = mapped_column("LANGSPOKEN", String(20))
    langprint: Mapped[str | None] = mapped_column("LANGPRINT", String(5))
    medaidcode: Mapped[str | None] = mapped_column("MEDAIDCODE", String(2))
    clientpc: Mapped[str | None] = mapped_column("CLIENTPC", String(3))
    dependencyrestart: Mapped[datetime | None] = mapped_column(
        "DEPENDENCYRESTART", DateTime
    )
    gptermdate: Mapped[datetime | None] = mapped_column("GPTERMDATE", DateTime)
    str1_90: Mapped[str | None] = mapped_column("STR1_90", String(90))
    str2_90: Mapped[str | None] = mapped_column("STR2_90", String(90))
    benyrstartoverride: Mapped[datetime | None] = mapped_column(
        "BENYRSTARTOVERRIDE", DateTime
    )
    dependencylkbkdays: Mapped[int | None] = mapped_column(
        "DEPENDENCYLKBKDAYS", Integer
    )
    dateofdeath: Mapped[datetime | None] = mapped_column("DATEOFDEATH", DateTime)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<Subscriber subscribernum={self.subscribernum!r} "
            f"personcode={self.personcode!r} clientcode={self.clientcode!r}>"
        )
