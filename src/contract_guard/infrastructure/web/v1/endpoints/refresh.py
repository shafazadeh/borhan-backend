from fastapi import APIRouter
from contract_guard.application.use_cases.refresh_session import refresh_session
from contract_guard.infrastructure.web.schemas import RefreshRequest, TokensResponse

router = APIRouter()


@router.post("/auth/refresh", response_model=TokensResponse)
def refresh(body: RefreshRequest):
    return refresh_session(body.refresh_token)
