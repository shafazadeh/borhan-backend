from fastapi import APIRouter
from contract_guard.infrastructure.web.schemas import MobileRequest
from contract_guard.application.use_cases.request_login import request_login

router = APIRouter()


@router.post("/auth/request-code")
def request_code(body: MobileRequest):
    return request_login(body.mobile)
