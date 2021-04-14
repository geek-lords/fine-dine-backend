import psycopg2
from contextlib2 import contextmanager

from config import connection_url


@contextmanager
def connection():
    conn = psycopg2.connect(connection_url)

    try:
        yield conn
    finally:
        conn.close()
