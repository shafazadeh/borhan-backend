from fastapi import HTTPException
from contract_guard.config.settings import Environment, Settings
from contract_guard.infrastructure.cache.create_challenge import create_challenge


def request_login(mobile: str):
    if Settings().environment != Environment.development:
        raise HTTPException(503, "SMS delivery is not configured")
    create_challenge(mobile)
    return {"message": "Verification code requested"}
