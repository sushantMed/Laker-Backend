from datetime import date
from enum import Enum


class MemberStatus(str, Enum):
    """Member eligibility status."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PENDING = "PENDING"


def derive_status(start_date: date, end_date: date) -> MemberStatus:
    today = date.today()
    if today < start_date:
        return MemberStatus.PENDING
    if today > end_date:
        return MemberStatus.INACTIVE
    return MemberStatus.ACTIVE


class Gender(str, Enum):
    """Member gender."""

    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"


class RelCode(str, Enum):
    """Relationship code — defines family role."""

    CARDHOLDER = "01"
    SPOUSE = "02"
    DEPENDENT_CHILD = "03"


class FamilyRole(str, Enum):
    """Human-readable family role derived from RelCode."""

    CARDHOLDER = "Cardholder"
    SPOUSE = "Spouse"
    DEPENDENT_CHILD = "Dependent Child"

    @classmethod
    def from_rel_code(cls, rel_code: str) -> "FamilyRole":
        mapping = {
            "01": cls.CARDHOLDER,
            "02": cls.SPOUSE,
        }
        if rel_code and rel_code >= "03":
            return cls.DEPENDENT_CHILD
        return mapping.get(rel_code, cls.DEPENDENT_CHILD)


class CoverageType(str, Enum):
    CARDHOLDER = "Cardholder Only"  # Cardholder Only
    FAMILY = "Family"
    SPOUSE = "Spouse"
    DEPENDENT = "Dependent"


class BrandGeneric(str, Enum):
    BRAND = "Brand Name"
    GENERIC = "Generic Name"
    ALL = "ALL"  # Represents both BRAND and GENERIC


class Maintenance(str, Enum):
    YES = "YES"
    NO = "NO"
