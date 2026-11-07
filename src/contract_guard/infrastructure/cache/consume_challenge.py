import hmac
from fastapi import HTTPException
from redis.exceptions import RedisError
from contract_guard.config.settings import Settings
from .challenge_keys import challenge_keys
from .redis_client import redis_client

SCRIPT = """
local attempts = redis.call('GET', KEYS[1])
if not attempts or tonumber(attempts) >= tonumber(ARGV[1]) then return 0 end
if ARGV[2] == '1' then
    redis.call('DEL', KEYS[1])
    return 1
end
redis.call('INCR', KEYS[1])
return 0
"""


def consume_challenge(mobile: str, code: str):
    settings = Settings()
    correct = int(hmac.compare_digest(code.encode(), settings.dev_otp_code.encode()))
    try:
        consumed = redis_client().eval(SCRIPT, 1, challenge_keys(mobile)[0], settings.otp_max_attempts, correct)
    except RedisError as exc:
        raise HTTPException(503, "Verification service unavailable") from exc
    if not consumed:
        raise HTTPException(400, "Verification code is invalid or expired")
