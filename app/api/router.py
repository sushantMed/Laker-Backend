from fastapi import APIRouter

from app.api.v1 import auth, health, users, members, drugs, pharmacies, prescribers

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(health.router)
api_router.include_router(members.router)
api_router.include_router(drugs.router)
api_router.include_router(pharmacies.router)
api_router.include_router(prescribers.router)
