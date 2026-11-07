from fastapi import APIRouter
from .endpoints import request_login, verify_login, profile, update_profile, logout, ingestion, refresh, taxonomy

router = APIRouter(prefix="/api/v1")
for module in (request_login, verify_login, profile, update_profile, logout, ingestion, refresh, taxonomy):
    router.include_router(module.router)
