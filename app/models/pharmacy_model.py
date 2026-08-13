from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class PharmacyModel(Base):
    __tablename__ = "pharmacies"

    nabp: Mapped[str] = mapped_column(
        String(7), unique=True, index=True, nullable=False
    )
    npi: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    pharmacy_name: Mapped[str] = mapped_column(String(255), nullable=False)
    pharm_name2: Mapped[str | None] = mapped_column(String(10), nullable=True)
    legal_name: Mapped[str | None] = mapped_column(String(60), nullable=True)
    doctor_name: Mapped[str | None] = mapped_column(String(60), nullable=True)

    # Physical address
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line2: Mapped[str | None] = mapped_column(String(55), nullable=True)
    address_line3: Mapped[str | None] = mapped_column(String(35), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    zip: Mapped[str] = mapped_column(String(10), nullable=False)
    county: Mapped[str | None] = mapped_column(String(50), nullable=True)
    county_fips_code: Mapped[str | None] = mapped_column(String(5), nullable=True)
    msa: Mapped[str | None] = mapped_column(String(4), nullable=True)
    pmsa: Mapped[str | None] = mapped_column(String(4), nullable=True)
    voting_district: Mapped[str | None] = mapped_column(String(4), nullable=True)
    directions: Mapped[str | None] = mapped_column(String(50), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric, nullable=True)

    # Mailing address
    mail_addr1: Mapped[str | None] = mapped_column(String(55), nullable=True)
    mail_addr2: Mapped[str | None] = mapped_column(String(55), nullable=True)
    mail_city: Mapped[str | None] = mapped_column(String(35), nullable=True)
    mail_state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    mail_zip: Mapped[str | None] = mapped_column(String(11), nullable=True)

    # Contact info
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    phone_ext: Mapped[str | None] = mapped_column(String(5), nullable=True)
    fax: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pharm_email: Mapped[str | None] = mapped_column(String(50), nullable=True)
    website: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hospice_phone: Mapped[str | None] = mapped_column(String(10), nullable=True)
    hospice_fax: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Primary contact person
    contact_first_name: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contact_last_name: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contact_mi: Mapped[str | None] = mapped_column(String(1), nullable=True)
    contact_title: Mapped[str | None] = mapped_column(String(30), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(10), nullable=True)
    contact_phone_ext: Mapped[str | None] = mapped_column(String(5), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Classification / dispensing
    disp_class: Mapped[str | None] = mapped_column(String(3), nullable=True)
    disp_type: Mapped[str | None] = mapped_column(String(3), nullable=True)
    disp_type2: Mapped[str | None] = mapped_column(String(2), nullable=True)
    disp_type3: Mapped[str | None] = mapped_column(String(2), nullable=True)
    dir_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dir_chain: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dir_class: Mapped[str | None] = mapped_column(String(50), nullable=True)
    jurisdiction: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Licensing / identifiers
    fed_licence: Mapped[str | None] = mapped_column(String(12), nullable=True)
    fed_tin: Mapped[str | None] = mapped_column(String(15), nullable=True)
    fed_expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    state_licence: Mapped[str | None] = mapped_column(String(20), nullable=True)
    state_license: Mapped[str | None] = mapped_column(String(20), nullable=True)
    state_tin: Mapped[str | None] = mapped_column(String(15), nullable=True)
    sl_expires: Mapped[date | None] = mapped_column(Date, nullable=True)
    medicaid_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    medicaid_provider_id: Mapped[str | None] = mapped_column(String(35), nullable=True)
    med_provider_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    dea: Mapped[str | None] = mapped_column(String(12), nullable=True)
    nppes_enum_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    deactivation_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    reinstatement_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    reinstatement_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Affiliation / payment center
    affiliation_code: Mapped[str | None] = mapped_column(String(3), nullable=True)
    affiliation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    pay_center_code: Mapped[str | None] = mapped_column(String(7), nullable=True)
    pay_center_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Banking / payment
    eft_route: Mapped[str | None] = mapped_column(String(9), nullable=True)
    routing_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    account_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ach: Mapped[str | None] = mapped_column(String(1), nullable=True)
    check_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    receiver_id_835: Mapped[str | None] = mapped_column(String(15), nullable=True)
    ncpdp_835_dir: Mapped[str | None] = mapped_column(String(50), nullable=True)
    remit_recon_id: Mapped[str | None] = mapped_column(String(6), nullable=True)
    remit_recon_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    payment_term_days: Mapped[int | None] = mapped_column(
        Integer, default=0, nullable=True
    )
    admin_fee: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    precinct_tax: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    intervention_perc: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    contracted: Mapped[str | None] = mapped_column(String(1), nullable=True)

    # Operating hours
    is_24_hour: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sun_hours: Mapped[str | None] = mapped_column(String(5), nullable=True)
    mon_hours: Mapped[str | None] = mapped_column(String(5), nullable=True)
    tue_hours: Mapped[str | None] = mapped_column(String(5), nullable=True)
    wed_hours: Mapped[str | None] = mapped_column(String(5), nullable=True)
    thu_hours: Mapped[str | None] = mapped_column(String(5), nullable=True)
    fri_hours: Mapped[str | None] = mapped_column(String(5), nullable=True)
    sat_hours: Mapped[str | None] = mapped_column(String(5), nullable=True)

    # Service capability flags/codes
    long_term_care_ind: Mapped[str | None] = mapped_column(String(1), nullable=True)
    assisted_living_ind: Mapped[str | None] = mapped_column(String(1), nullable=True)
    accept_erx_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    delivery_service_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    compounding_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    drive_up_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    dme_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    walkin_clinic_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    hh24_emergency_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    multidose_pkg_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    immunization_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    handicap_access_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    status_340b_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    closed_door_facility_code: Mapped[str | None] = mapped_column(
        String(2), nullable=True
    )
    pservices_other: Mapped[str | None] = mapped_column(String(25), nullable=True)
    lang_bf: Mapped[int | None] = mapped_column(Integer, nullable=True)
    service_bf: Mapped[int | None] = mapped_column(Integer, nullable=True)
    service_bf2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bit_flags: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bit_flags2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prior_auth_flags: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # eRx
    erx_network_id: Mapped[str | None] = mapped_column(String(3), nullable=True)
    erx_service_level_codes: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    erx_effective_from_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    erx_effective_thru_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Credentialing / lifecycle dates
    open_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_entered: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_termed: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_cred: Mapped[date | None] = mapped_column(Date, nullable=True)
    recred_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    mod_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    mod_user: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Misc
    test_only: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    no_update: Mapped[str | None] = mapped_column(String(1), nullable=True)
    file_media: Mapped[str | None] = mapped_column(String(10), nullable=True)

    in_network: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

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
