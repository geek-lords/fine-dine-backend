from flask import Blueprint

from db_utils import connection

admin = Blueprint('admin', __name__)


@admin.route('/version')
def version():
    with connection() as conn, conn.cursor() as cur:
        cur.execute('select version()')
        return {
            'version': cur.fetchone()[0],
        }
