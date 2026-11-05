from pathlib import Path

import psycopg

from app.config import database_url


def main():
    migration = Path(__file__).resolve().parent.parent / "migrations" / "001_create_users.sql"
    with psycopg.connect(database_url()) as connection:
        connection.execute(migration.read_text(encoding="utf-8"))
    print("User migration applied")


if __name__ == "__main__":
    main()
