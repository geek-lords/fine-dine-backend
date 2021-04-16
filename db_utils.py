import pymysql
from contextlib2 import contextmanager

from config import username, password, hostname, database


@contextmanager
def connection():
    conn = pymysql.connect(user=username, password=password, host=hostname, database=database)

    try:
        yield conn
    finally:
        conn.close()
