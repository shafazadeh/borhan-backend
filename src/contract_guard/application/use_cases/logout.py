from contract_guard.infrastructure.database.session import database


def logout(session_id):
    with database() as connection:
        connection.execute("UPDATE login_sessions SET revoked_at=CURRENT_TIMESTAMP WHERE id=%s", (session_id,))
