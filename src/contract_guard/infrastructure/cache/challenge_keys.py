import hashlib
from contract_guard.config.settings import Settings


def challenge_keys(mobile: str):
    digest = hashlib.sha256(mobile.encode()).hexdigest()
    prefix = f"{Settings().redis_key_prefix}:{{{digest}}}"
    return f"{prefix}:challenge", f"{prefix}:cooldown"
