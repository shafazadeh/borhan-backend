from fastapi import APIRouter, Depends, Response
from contract_guard.application.use_cases.logout import logout
from contract_guard.infrastructure.web.dependencies import current_session

router = APIRouter()


@router.post("/auth/logout", status_code=204)
def logout_session(user=Depends(current_session)):
    logout(user["session_id"])
    return Response(status_code=204)
