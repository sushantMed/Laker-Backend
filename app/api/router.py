from fastapi import APIRouter

from app.api.v1 import (
    auth,
    claims,
    drugs,
    health,
    members,
    pharmacies,
    prescribers,
    users,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(health.router)
api_router.include_router(claims.router)
api_router.include_router(members.router)
api_router.include_router(drugs.router)
api_router.include_router(pharmacies.router)
api_router.include_router(prescribers.router)
