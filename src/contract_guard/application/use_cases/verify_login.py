from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from uuid import uuid4
from fastapi import HTTPException
from contract_guard.config.settings import Environment, Settings
from contract_guard.infrastructure.cache.consume_challenge import consume_challenge
from contract_guard.infrastructure.database.session import database


def verify_login(mobile: str, code: str):
    settings = Settings()
    if settings.environment != Environment.development:
        raise HTTPException(503, "SMS delivery is not configured")
    consume_challenge(mobile, code)
    with database() as connection:
        user = connection.execute("""INSERT INTO users (id, mobile_number) VALUES (%s, %s)
            ON CONFLICT (mobile_number) DO UPDATE SET mobile_number=EXCLUDED.mobile_number
            RETURNING id, mobile_number, email, username""", (uuid4(), mobile)).fetchone()
        access_token, refresh_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        session_expires = now + timedelta(hours=settings.session_hours)
        access_expires = min(now + timedelta(minutes=settings.access_token_minutes), session_expires)
        connection.execute("""INSERT INTO login_sessions
            (id,user_id,token_hash,refresh_token_hash,access_expires_at,expires_at)
            VALUES (%s,%s,%s,%s,%s,%s)""", (uuid4(), user["id"],
            hashlib.sha256(access_token.encode()).hexdigest(), hashlib.sha256(refresh_token.encode()).hexdigest(),
            access_expires, session_expires))
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer",
            "expires_at": access_expires, "refresh_expires_at": session_expires, "user": user}
