from fastapi import APIRouter
from .endpoints import request_login, verify_login, profile, update_profile, logout, ingestion, refresh, taxonomy, chunking

router = APIRouter(prefix="/api/v1")
for module in (request_login, verify_login, profile, update_profile, logout, ingestion, refresh, taxonomy, chunking):
    router.include_router(module.router)
