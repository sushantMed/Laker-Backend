from datetime import date

from sqlalchemy import Boolean, Date, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import LookupBase


class PharmacyModel(LookupBase):
    __tablename__ = "pharmacies"

    nabp: Mapped[str] = mapped_column(
        "NABP", String(7), primary_key=True, unique=True, index=True
    )
    npi: Mapped[str] = mapped_column(
        "NPI", String(10), unique=True, index=True, nullable=False
    )
    pharmacy_name: Mapped[str] = mapped_column(
        "PHARMACYNAME", String(60), nullable=False
    )
    pharm_name2: Mapped[str | None] = mapped_column(
        "PHARMNAME2", String(10), nullable=True
    )
    legal_name: Mapped[str | None] = mapped_column(
        "LEGALNAME", String(60), nullable=True
    )
    doctor_name: Mapped[str | None] = mapped_column(
        "DOCTORNAME", String(60), nullable=True
    )

    # Physical address
    address_line1: Mapped[str] = mapped_column("PHARMADDR1", String(55), nullable=False)
    address_line2: Mapped[str | None] = mapped_column(
        "PHARMADDR2", String(55), nullable=True
    )
    address_line3: Mapped[str | None] = mapped_column(
        "PHARMADDR3", String(35), nullable=True
    )
    city: Mapped[str] = mapped_column("PHARMCITY", String(35), nullable=False)
    state: Mapped[str] = mapped_column("PHARMSTATE", String(5), nullable=False)
    zip: Mapped[str] = mapped_column("PHARMZIP", String(11), nullable=False)
    county: Mapped[str | None] = mapped_column("COUNTY", String(50), nullable=True)
    county_fips_code: Mapped[str | None] = mapped_column(
        "COUNTYFIPSCODE", String(5), nullable=True
    )
    msa: Mapped[str | None] = mapped_column("MSA", String(4), nullable=True)
    pmsa: Mapped[str | None] = mapped_column("PMSA", String(4), nullable=True)
    voting_district: Mapped[str | None] = mapped_column(
        "VOTINGDISTRICT", String(4), nullable=True
    )
    directions: Mapped[str | None] = mapped_column(
        "DIRECTIONS", String(50), nullable=True
    )
    latitude: Mapped[float | None] = mapped_column("LATITUDE", Numeric, nullable=True)
    longitude: Mapped[float | None] = mapped_column("LONGITUDE", Numeric, nullable=True)

    # Mailing address
    mail_addr1: Mapped[str | None] = mapped_column(
        "MAILADDR1", String(55), nullable=True
    )
    mail_addr2: Mapped[str | None] = mapped_column(
        "MAILADDR2", String(55), nullable=True
    )
    mail_city: Mapped[str | None] = mapped_column("MAILCITY", String(35), nullable=True)
    mail_state: Mapped[str | None] = mapped_column(
        "MAILSTATE", String(2), nullable=True
    )
    mail_zip: Mapped[str | None] = mapped_column("MAILZIP", String(11), nullable=True)

    # Contact info
    phone: Mapped[str] = mapped_column("PHONE", String(10), nullable=False)
    phone_ext: Mapped[str | None] = mapped_column(
        "PHARMPHONEEXT", String(5), nullable=True
    )
    fax: Mapped[str | None] = mapped_column("FAX", String(10), nullable=True)
    email: Mapped[str | None] = mapped_column("EMAIL", String(100), nullable=True)
    pharm_email: Mapped[str | None] = mapped_column(
        "PHARMEMAIL", String(50), nullable=True
    )
    website: Mapped[str | None] = mapped_column("WEBSITE", String(50), nullable=True)
    hospice_phone: Mapped[str | None] = mapped_column(
        "HOSPICEPHONE", String(10), nullable=True
    )
    hospice_fax: Mapped[str | None] = mapped_column(
        "HOSPICEFAX", String(10), nullable=True
    )

    # Primary contact person
    contact_first_name: Mapped[str | None] = mapped_column(
        "CONTACTFIRSTNAME", String(20), nullable=True
    )
    contact_last_name: Mapped[str | None] = mapped_column(
        "CONTACTLASTNAME", String(20), nullable=True
    )
    contact_mi: Mapped[str | None] = mapped_column(
        "CONTACTMI", String(1), nullable=True
    )
    contact_title: Mapped[str | None] = mapped_column(
        "CONTACTTITLE", String(30), nullable=True
    )
    contact_phone: Mapped[str | None] = mapped_column(
        "CONTACTPHONE", String(10), nullable=True
    )
    contact_phone_ext: Mapped[str | None] = mapped_column(
        "CONTACTPHONEEXT", String(5), nullable=True
    )
    contact_email: Mapped[str | None] = mapped_column(
        "CONTACTEMAIL", String(50), nullable=True
    )

    # Classification / dispensing
    disp_class: Mapped[str | None] = mapped_column(
        "DISPCLASS", String(3), nullable=True
    )
    disp_type: Mapped[str | None] = mapped_column("DISPTYPE", String(3), nullable=True)
    disp_type2: Mapped[str | None] = mapped_column(
        "DISPTYPE2", String(2), nullable=True
    )
    disp_type3: Mapped[str | None] = mapped_column(
        "DISPTYPE3", String(2), nullable=True
    )
    dir_name: Mapped[str | None] = mapped_column("DIRNAME", String(50), nullable=True)
    dir_chain: Mapped[str | None] = mapped_column("DIRCHAIN", String(50), nullable=True)
    dir_class: Mapped[str | None] = mapped_column("DIRCLASS", String(50), nullable=True)
    jurisdiction: Mapped[str | None] = mapped_column(
        "JURISDICTION", String(10), nullable=True
    )

    # Licensing / identifiers
    fed_licence: Mapped[str | None] = mapped_column(
        "FEDLICENCE", String(12), nullable=True
    )
    fed_tin: Mapped[str | None] = mapped_column("FEDTIN", String(15), nullable=True)
    fed_expiration_date: Mapped[date | None] = mapped_column(
        "FEDEXPIRATIONDATE", Date, nullable=True
    )
    state_licence: Mapped[str | None] = mapped_column(
        "STATELICENCE", String(20), nullable=True
    )
    state_license: Mapped[str | None] = mapped_column(
        "STATELICENSE", String(20), nullable=True
    )
    state_tin: Mapped[str | None] = mapped_column("STATETIN", String(15), nullable=True)
    sl_expires: Mapped[date | None] = mapped_column("SLEXPIRES", Date, nullable=True)
    medicaid_id: Mapped[str | None] = mapped_column(
        "MEDICAIDID", String(20), nullable=True
    )
    medicaid_provider_id: Mapped[str | None] = mapped_column(
        "MEDICAIDPROVIDERID", String(35), nullable=True
    )
    med_provider_id: Mapped[str | None] = mapped_column(
        "MEDPROVIDERID", String(20), nullable=True
    )
    dea: Mapped[str | None] = mapped_column("DEA", String(12), nullable=True)
    nppes_enum_date: Mapped[date | None] = mapped_column(
        "NPPESENUMDATE", Date, nullable=True
    )
    deactivation_code: Mapped[str | None] = mapped_column(
        "DEACTIVATIONCODE", String(2), nullable=True
    )
    reinstatement_code: Mapped[str | None] = mapped_column(
        "REINSTATEMENTCODE", String(2), nullable=True
    )
    reinstatement_date: Mapped[date | None] = mapped_column(
        "REINSTATEMENTDATE", Date, nullable=True
    )

    # Affiliation / payment center
    affiliation_code: Mapped[str | None] = mapped_column(
        "AFFILIATIONCODE", String(3), nullable=True
    )
    affiliation_date: Mapped[date | None] = mapped_column(
        "AFFILIATIONDATE", Date, nullable=True
    )
    pay_center_code: Mapped[str | None] = mapped_column(
        "PAYCENTERCODE", String(7), nullable=True
    )
    pay_center_date: Mapped[date | None] = mapped_column(
        "PAYCENTERDATE", Date, nullable=True
    )

    # Banking / payment
    eft_route: Mapped[str | None] = mapped_column("EFTROUTE", String(9), nullable=True)
    routing_number: Mapped[str | None] = mapped_column(
        "ROUTINGNUMBER", String(20), nullable=True
    )
    account_number: Mapped[str | None] = mapped_column(
        "ACCOUNTNUMBER", String(20), nullable=True
    )
    ach: Mapped[str | None] = mapped_column("ACH", String(1), nullable=True)
    check_type: Mapped[str | None] = mapped_column(
        "CHECKTYPE", String(10), nullable=True
    )
    receiver_id_835: Mapped[str | None] = mapped_column(
        "RECEIVERID835", String(15), nullable=True
    )
    ncpdp_835_dir: Mapped[str | None] = mapped_column(
        "NCPDP835DIR", String(50), nullable=True
    )
    remit_recon_id: Mapped[str | None] = mapped_column(
        "REMITRECONID", String(6), nullable=True
    )
    remit_recon_date: Mapped[date | None] = mapped_column(
        "REMITRECONDATE", Date, nullable=True
    )
    payment_term_days: Mapped[int | None] = mapped_column(
        "PAYMENTTERMDAYS", Integer, default=0, nullable=True
    )
    admin_fee: Mapped[float | None] = mapped_column("ADMINFEE", Numeric, nullable=True)
    precinct_tax: Mapped[float | None] = mapped_column(
        "PRECINCTTAX", Numeric, nullable=True
    )
    intervention_perc: Mapped[float | None] = mapped_column(
        "INTERVENTIONPERC", Numeric, nullable=True
    )
    contracted: Mapped[str | None] = mapped_column(
        "CONTRACTED", String(1), nullable=True
    )

    # Operating hours
    is_24_hour: Mapped[bool] = mapped_column(
        "FLAG24HOURS", Boolean, nullable=False, default=False
    )
    sun_hours: Mapped[str | None] = mapped_column("SUNHOURS", String(5), nullable=True)
    mon_hours: Mapped[str | None] = mapped_column("MONHOURS", String(5), nullable=True)
    tue_hours: Mapped[str | None] = mapped_column("TUEHOURS", String(5), nullable=True)
    wed_hours: Mapped[str | None] = mapped_column("WEDHOURS", String(5), nullable=True)
    thu_hours: Mapped[str | None] = mapped_column("THUHOURS", String(5), nullable=True)
    fri_hours: Mapped[str | None] = mapped_column("FRIHOURS", String(5), nullable=True)
    sat_hours: Mapped[str | None] = mapped_column("SATHOURS", String(5), nullable=True)

    # Service capability flags/codes
    long_term_care_ind: Mapped[str | None] = mapped_column(
        "LONGTERMCAREIND", String(1), nullable=True
    )
    assisted_living_ind: Mapped[str | None] = mapped_column(
        "ASSISTEDLIVINGIND", String(1), nullable=True
    )
    accept_erx_code: Mapped[str | None] = mapped_column(
        "ACCEPTERXCODE", String(2), nullable=True
    )
    delivery_service_code: Mapped[str | None] = mapped_column(
        "DELIVERYSERVICECODE", String(2), nullable=True
    )
    compounding_code: Mapped[str | None] = mapped_column(
        "COMPOUNDINGCODE", String(2), nullable=True
    )
    drive_up_code: Mapped[str | None] = mapped_column(
        "DRIVEUPCODE", String(2), nullable=True
    )
    dme_code: Mapped[str | None] = mapped_column("DMECODE", String(2), nullable=True)
    walkin_clinic_code: Mapped[str | None] = mapped_column(
        "WALKINCLINICCODE", String(2), nullable=True
    )
    hh24_emergency_code: Mapped[str | None] = mapped_column(
        "HH24EMERGENCYCODE", String(2), nullable=True
    )
    multidose_pkg_code: Mapped[str | None] = mapped_column(
        "MULTIDOSEPKGCODE", String(2), nullable=True
    )
    immunization_code: Mapped[str | None] = mapped_column(
        "IMMUNIZATIONCODE", String(2), nullable=True
    )
    handicap_access_code: Mapped[str | None] = mapped_column(
        "HANDICAPACCESSCODE", String(2), nullable=True
    )
    status_340b_code: Mapped[str | None] = mapped_column(
        "STATUS340BCODE", String(2), nullable=True
    )
    closed_door_facility_code: Mapped[str | None] = mapped_column(
        "CLOSEDDOORFACILITYCODE", String(2), nullable=True
    )
    pservices_other: Mapped[str | None] = mapped_column(
        "PSERVICESOTHER", String(25), nullable=True
    )
    lang_bf: Mapped[int | None] = mapped_column("LANGBF", Integer, nullable=True)
    service_bf: Mapped[int | None] = mapped_column("SERVICEBF", Integer, nullable=True)
    service_bf2: Mapped[int | None] = mapped_column(
        "SERVICEBF2", Integer, nullable=True
    )
    bit_flags: Mapped[int | None] = mapped_column("BITFLAGS", Integer, nullable=True)
    bit_flags2: Mapped[int | None] = mapped_column("BITFLAGS2", Integer, nullable=True)
    prior_auth_flags: Mapped[int | None] = mapped_column(
        "PRIORAUTHFLAGS", Integer, nullable=True
    )

    # eRx
    erx_network_id: Mapped[str | None] = mapped_column(
        "ERXNETWORKID", String(3), nullable=True
    )
    erx_service_level_codes: Mapped[str | None] = mapped_column(
        "ERXSERVICELEVELCODES", String(100), nullable=True
    )
    erx_effective_from_date: Mapped[date | None] = mapped_column(
        "ERXEFFECTIVEFROMDATE", Date, nullable=True
    )
    erx_effective_thru_date: Mapped[date | None] = mapped_column(
        "ERXEFFECTIVETHRUDATE", Date, nullable=True
    )

    # Credentialing / lifecycle dates
    open_date: Mapped[date | None] = mapped_column("OPENDATE", Date, nullable=True)
    date_entered: Mapped[date | None] = mapped_column(
        "DATEENTERED", Date, nullable=True
    )
    date_termed: Mapped[date | None] = mapped_column("DATETERMED", Date, nullable=True)
    date_cred: Mapped[date | None] = mapped_column("DATECRED", Date, nullable=True)
    recred_date: Mapped[date | None] = mapped_column("RECREDDATE", Date, nullable=True)
    mod_date: Mapped[date | None] = mapped_column("MODDATE", Date, nullable=True)
    mod_user: Mapped[str | None] = mapped_column("MODUSER", String(20), nullable=True)

    # Misc
    test_only: Mapped[bool | None] = mapped_column("TESTONLY", Boolean, nullable=True)
    no_update: Mapped[str | None] = mapped_column("NOUPDATE", String(1), nullable=True)
    file_media: Mapped[str | None] = mapped_column(
        "FILEMEDIA", String(10), nullable=True
    )
