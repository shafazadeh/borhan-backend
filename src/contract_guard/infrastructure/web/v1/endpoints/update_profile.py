from fastapi import APIRouter, Depends
from contract_guard.application.use_cases.update_profile import update_profile
from contract_guard.infrastructure.web.dependencies import current_session
from contract_guard.infrastructure.web.schemas import ProfileUpdate

router = APIRouter()


@router.patch("/users/me")
def profile_update(body: ProfileUpdate, user=Depends(current_session)):
    return update_profile(user["id"], body.model_dump(exclude_unset=True))
