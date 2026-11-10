from alembic import context
from sqlalchemy import create_engine
from contract_guard.config.settings import Settings
from contract_guard.infrastructure.database.models import Base

target_metadata = Base.metadata

def run_migrations_offline():
    context.configure(url=Settings().database_url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    engine = create_engine(Settings().database_url.replace("postgresql://", "postgresql+psycopg://", 1))
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, include_object=lambda obj, name, type_, reflected, compare_to: not (type_ == "table" and reflected and compare_to is None))
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
