import hashlib
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from contract_guard.infrastructure.database.session import database

bearer = HTTPBearer(auto_error=False)


def current_session(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Bearer"})
    digest = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    with database() as connection:
        row = connection.execute("""SELECT u.id, u.mobile_number, u.email, u.username, s.id AS session_id
            FROM login_sessions s JOIN users u ON u.id=s.user_id
            WHERE s.token_hash=%s AND s.revoked_at IS NULL AND s.expires_at > CURRENT_TIMESTAMP AND s.access_expires_at > CURRENT_TIMESTAMP""", (digest,)).fetchone()
    if not row:
        raise HTTPException(401, "Session invalid or expired", headers={"WWW-Authenticate": "Bearer"})
    return row
