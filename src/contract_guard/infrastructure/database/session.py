from contextlib import contextmanager
import psycopg
from psycopg.rows import dict_row
from contract_guard.config.settings import Settings


@contextmanager
def database():
    with psycopg.connect(Settings().database_url, row_factory=dict_row) as connection:
        yield connection
