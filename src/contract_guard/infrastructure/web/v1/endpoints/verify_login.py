from fastapi import APIRouter
from contract_guard.infrastructure.web.schemas import VerifyRequest, LoginResponse
from contract_guard.application.use_cases.verify_login import verify_login

router = APIRouter()


@router.post("/auth/verify", response_model=LoginResponse)
def verify_code(body: VerifyRequest):
    return verify_login(body.mobile, body.code)
