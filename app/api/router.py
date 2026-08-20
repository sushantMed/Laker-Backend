from fastapi import APIRouter

from app.api.v1 import (
    auth,
    claims,
    drugs,
    eligibility,
    health,
    members,
    pharmacies,
    prescribers,
    prior_auth,
    users,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(health.router)
api_router.include_router(claims.router)
# eligibility.router must be registered before members.router: both mount under
# /members, and members.router's GET /{member_id} would otherwise swallow
# /members/group-eligibility (member_id="group-eligibility") since Starlette
# matches routes in registration order.
api_router.include_router(eligibility.router)
api_router.include_router(members.router)
api_router.include_router(drugs.router)
api_router.include_router(pharmacies.router)
api_router.include_router(prescribers.router)
api_router.include_router(prior_auth.router)
