from redis import Redis
from contract_guard.config.settings import Settings


def redis_client():
    settings = Settings()
    return Redis.from_url(settings.redis_url, decode_responses=True,
                          socket_connect_timeout=settings.redis_socket_timeout_seconds,
                          socket_timeout=settings.redis_socket_timeout_seconds)
