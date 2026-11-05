import os
from dataclasses import dataclass
from pathlib import Path


def setting(name: str, default: str = "") -> str:
    configured = os.environ.get(name)
    if configured is not None:
        return configured
    local_config = Path(__file__).resolve().parent.parent / ".env"
    if local_config.is_file():
        for line in local_config.read_text(encoding="utf-8-sig").splitlines():
            key, separator, value = line.partition("=")
            if separator and key.strip() == name:
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                return value
    return default


def database_url() -> str:
    return setting("DATABASE_URL", "postgresql://localhost/borhan")


@dataclass(frozen=True)
class Settings:
    database_url: str
    redis_url: str
    token_secret: str
    environment: str
    model_concurrency: int

    @classmethod
    def from_environment(cls) -> "Settings":
        token_secret = setting("BORHAN_TOKEN_SECRET")
        if not token_secret:
            raise RuntimeError("BORHAN_TOKEN_SECRET must be configured")
        try:
            concurrency = int(setting("BORHAN_MODEL_CONCURRENCY", "2"))
            if concurrency < 1:
                raise ValueError
        except ValueError as exc:
            raise RuntimeError("BORHAN_MODEL_CONCURRENCY must be a positive integer") from exc
        return cls(
            database_url=database_url(),
            redis_url=setting("REDIS_URL", "redis://localhost:56379/0"),
            token_secret=token_secret,
            environment=setting("BORHAN_ENV", "production"),
            model_concurrency=concurrency,
        )
