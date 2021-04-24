from flask import Blueprint, request
import requests
import qrcode
from uuid import uuid4
from random import randint
from PIL import Image

from db_utils import connection

admin = Blueprint('admin', __name__)


# HTTP Errors
ValidationError = 422


@admin.route('/version')
def version():
    with connection() as conn, conn.cursor() as cur:
        cur.execute('select version()')
        return {
            'version': cur.fetchone()[0],
        }


@admin.route("/generate_qr", methods=['GET'])
def generate_qr():
    if not request.json:
        return {'error': 'No json data found'}, ValidationError
