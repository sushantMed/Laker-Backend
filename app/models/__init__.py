"""Import all ORM models so their mappers are registered on `import app.models`.

Relationships reference other models by class name (e.g. MemberModel.plan ->
"PlanModel"). SQLAlchemy can only resolve those names once every model class has
been imported, so any entry point that queries the DB (scripts, etc.) should
import this package to guarantee the full registry is configured.
"""

from app.models.auth_model import RefreshTokenModel, RevokedAccessTokenModel
from app.models.claim_model import ClaimModel
from app.models.drug_model import DrugModel
from app.models.member_address_model import MemberAddressModel
from app.models.member_model import MemberModel
from app.models.pharmacy_model import PharmacyModel
from app.models.plan_model import PlanModel
from app.models.prescriber_model import PrescriberModel
from app.models.user_model import UserModel

__all__ = [
    "ClaimModel",
    "DrugModel",
    "MemberAddressModel",
    "MemberModel",
    "PharmacyModel",
    "PlanModel",
    "PrescriberModel",
    "RefreshTokenModel",
    "RevokedAccessTokenModel",
    "UserModel",
]
