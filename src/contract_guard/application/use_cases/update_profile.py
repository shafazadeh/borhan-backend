from contract_guard.infrastructure.database.session import database


def update_profile(user_id, changes):
    with database() as connection:
        user = connection.execute("SELECT id, mobile_number, email, username FROM users WHERE id=%s FOR UPDATE", (user_id,)).fetchone()
        user.update(changes)
        connection.execute("UPDATE users SET email=%s, username=%s WHERE id=%s", (user["email"], user["username"], user_id))
        return user
