from fastapi import APIRouter, Depends
from contract_guard.infrastructure.web.dependencies import current_session

router = APIRouter()


@router.get("/users/me")
def profile(user=Depends(current_session)):
    return {key: value for key, value in user.items() if key != "session_id"}
