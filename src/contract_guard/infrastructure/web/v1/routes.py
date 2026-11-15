from fastapi import APIRouter
from .endpoints import contracts, request_login, verify_login, profile, update_profile, logout, ingestion, refresh, taxonomy, chunking, embedding

router = APIRouter(prefix="/api/v1")
for module in (request_login, verify_login, profile, update_profile, logout, ingestion, refresh, taxonomy, chunking, embedding, contracts):
    router.include_router(module.router)
