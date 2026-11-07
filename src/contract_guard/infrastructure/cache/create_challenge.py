from fastapi import HTTPException
from redis.exceptions import RedisError
from contract_guard.config.settings import Settings
from .challenge_keys import challenge_keys
from .redis_client import redis_client

SCRIPT = """
if redis.call('EXISTS', KEYS[2]) == 1 then return 0 end
redis.call('SET', KEYS[1], 0, 'EX', ARGV[1])
redis.call('SET', KEYS[2], 1, 'EX', ARGV[2])
return 1
"""


def create_challenge(mobile: str):
    settings = Settings()
    try:
        created = redis_client().eval(SCRIPT, 2, *challenge_keys(mobile),
                                      settings.otp_minutes * 60, settings.otp_request_cooldown_seconds)
    except RedisError as exc:
        raise HTTPException(503, "Verification service unavailable") from exc
    if not created:
        raise HTTPException(429, "Please wait before requesting another code")
