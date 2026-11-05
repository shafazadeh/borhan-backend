import hmac
import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import psycopg
import redis
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator


router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
bearer = HTTPBearer(auto_error=False)


class MobileRequest(BaseModel):
    mobile: str = Field(examples=["09123456789"])

    @field_validator("mobile")
    @classmethod
    def normalize_mobile(cls, value: str) -> str:
        value = value.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
        value = re.sub(r"[\s-]", "", value)
        if value.startswith("+98"):
            value = "0" + value[3:]
        elif value.startswith("0098"):
            value = "0" + value[4:]
        if not re.fullmatch(r"09[0-9]{9}", value):
            raise ValueError("Invalid mobile number")
        return value


class VerifyRequest(MobileRequest):
    code: str = Field(examples=["1234"])


def cache(request: Request) -> redis.Redis:
    return redis.Redis.from_url(request.app.state.settings.redis_url, decode_responses=True)


def require_development(request: Request) -> None:
    if request.app.state.settings.environment != "development":
        raise HTTPException(status_code=503, detail="Mobile sign-in is unavailable")


def limit(client: redis.Redis, key: str, maximum: int, seconds: int) -> None:
    script = "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]) end; return n"
    if client.eval(script, 1, key, seconds) > maximum:
        raise HTTPException(status_code=429, detail="Too many requests")


@router.post("/request-code")
def request_code(body: MobileRequest, request: Request):
    require_development(request)
    client = cache(request)
    limit(client, f"auth:request:{body.mobile}", 5, 600)
    client.set(f"auth:challenge:{body.mobile}", "pending", ex=300)
    return {"detail": "Verification requested"}


@router.post("/verify")
def verify_code(body: VerifyRequest, request: Request):
    require_development(request)
    client = cache(request)
    limit(client, f"auth:verify:{body.mobile}", 5, 600)
    if not client.exists(f"auth:challenge:{body.mobile}") or not hmac.compare_digest(body.code, "1234"):
        raise HTTPException(status_code=401, detail="Invalid verification code")
    settings = request.app.state.settings
    try:
        with psycopg.connect(settings.database_url) as connection:
            row = connection.execute(
                "INSERT INTO users (id, mobile_number) VALUES (%s, %s) "
                "ON CONFLICT (mobile_number) DO UPDATE SET mobile_number = EXCLUDED.mobile_number RETURNING id",
                (uuid4(), body.mobile),
            ).fetchone()
    except psycopg.Error:
        raise HTTPException(status_code=503, detail="Database unavailable; check DATABASE_URL and migration") from None
    if not client.delete(f"auth:challenge:{body.mobile}"):
        raise HTTPException(status_code=401, detail="Invalid verification code")
    token = jwt.encode(
        {"sub": str(row[0]), "exp": datetime.now(timezone.utc) + timedelta(hours=24)},
        settings.token_secret,
        algorithm="HS256",
    )
    return {"access_token": token, "token_type": "bearer"}


def current_user(request: Request, credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    if not credentials or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    token = credentials.credentials
    settings = request.app.state.settings
    try:
        user_id = jwt.decode(token, settings.token_secret, algorithms=["HS256"], options={"require": ["exp", "sub"]})["sub"]
        from uuid import UUID
        UUID(user_id)
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid authentication") from None
    with psycopg.connect(settings.database_url) as connection:
        user = connection.execute("SELECT id FROM users WHERE id = %s", (user_id,)).fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    return str(user[0])
