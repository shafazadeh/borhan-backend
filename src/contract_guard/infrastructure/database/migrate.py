from pathlib import Path
from contract_guard.infrastructure.database.session import database


def migrate():
    migrations = Path(__file__).resolve().parents[4] / "migrations"
    with database() as connection:
        for path in sorted(migrations.glob("[0-9]*.sql")):
            connection.execute(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    migrate()
