from enum import Enum
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    development = "development"
    production = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    environment: Environment
    database_url: str
    redis_url: str
    redis_key_prefix: str
    redis_socket_timeout_seconds: int = Field(ge=1, le=30)
    session_hours: int = Field(ge=1, le=24)
    access_token_minutes: int = Field(ge=1, le=1440)
    otp_minutes: int = Field(ge=1, le=30)
    otp_max_attempts: int = Field(ge=1, le=10)
    otp_request_cooldown_seconds: int = Field(ge=1)
    dev_otp_code: str
    host: str
    port: int = Field(ge=1, le=65535)
    upload_max_bytes: int = Field(ge=1)
    extraction_timeout_seconds: int = Field(ge=1, le=300)
    extraction_max_pages: int = Field(ge=1, le=5000)
    extraction_max_chars: int = Field(ge=1)
    docx_max_entries: int = Field(ge=1)
    docx_max_uncompressed_bytes: int = Field(ge=1)
    docx_max_compression_ratio: int = Field(ge=1)
    taxonomy_llm_url: str
    taxonomy_llm_model: str
    taxonomy_llm_api_key: str
    taxonomy_llm_timeout_seconds: int = Field(ge=1, le=120)
    taxonomy_llm_max_chars: int = Field(ge=100, le=10000)
    taxonomy_llm_concurrency: int = Field(ge=1, le=32)
