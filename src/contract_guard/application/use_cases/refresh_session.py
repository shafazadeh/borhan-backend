from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from fastapi import HTTPException
from contract_guard.config.settings import Settings
from contract_guard.infrastructure.database.session import database


def refresh_session(refresh_token: str):
    digest = hashlib.sha256(refresh_token.encode()).hexdigest()
    with database() as connection:
        session = connection.execute("""SELECT id, user_id, expires_at FROM login_sessions
            WHERE refresh_token_hash=%s AND revoked_at IS NULL AND expires_at > CURRENT_TIMESTAMP
            FOR UPDATE""", (digest,)).fetchone()
        if not session:
            raise HTTPException(401, "Refresh token invalid or expired")
        now = datetime.now(timezone.utc)
        access_expires = min(now + timedelta(minutes=Settings().access_token_minutes), session["expires_at"])
        if access_expires <= now:
            raise HTTPException(401, "Refresh token invalid or expired")
        new_access, new_refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        connection.execute("""UPDATE login_sessions SET token_hash=%s, refresh_token_hash=%s,
            access_expires_at=%s WHERE id=%s""", (hashlib.sha256(new_access.encode()).hexdigest(),
            hashlib.sha256(new_refresh.encode()).hexdigest(), access_expires, session["id"]))
    return {"access_token": new_access, "refresh_token": new_refresh, "token_type": "bearer",
            "expires_at": access_expires, "refresh_expires_at": session["expires_at"]}
