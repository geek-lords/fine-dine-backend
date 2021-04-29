from uuid import uuid4

import jwt
import qrcode
from flask import Blueprint, request, send_from_directory
from jwt import InvalidSignatureError
from werkzeug.urls import url_encode

from config import jwt_secret
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


def authenticate(_requests):
    try:
        decoded_jwt = jwt.decode(_requests.headers['X-Auth-Token'], jwt_secret, algorithms=['HS256'])
        admin_id = decoded_jwt['user_id']
        is_admin = decoded_jwt['is_admin']
        if not is_admin:
            raise ValidationError
        return admin_id
    except InvalidSignatureError:
        return None
    except KeyError:
        return None
    except ValidationError:
        return {'error': "Requested User isn't Admin."}


@admin.route("/code", methods=['GET'])
def generate_code():
    try:
        admin_id = authenticate(request)
        restaurant_id = request.args.get('restaurant_id')
        table = request.args.get('table')

        if admin_id is None or restaurant_id is None or table is None:
            raise TypeError
        with connection() as conn, conn.cursor() as cur:
            cur.execute("Select name from restaurant where id = %s && admin_id = %s", (restaurant_id, admin_id,))
            if cur.rowcount == 0:
                return {'error': "Restaurant and Admin Pair doesn't exists."}
            cur.execute("Select * from tables where restaurant_id = %s && name = %s", (restaurant_id, table))
            if cur.rowcount == 0:
                return {'error': "Restaurant and Table Pair doesn't exists."}

        params = {'restaurant_id': restaurant_id, 'table': table}
        img = qrcode.make('http://localhost:5000/api/v1/menu?' + url_encode(params))

        # if two people request qr code at almost same time, using the
        # same file will corrupt at least one response
        filename = f'{restaurant_id}-{table}-{uuid4()}.png'
        img.save('statics/qr/' + filename)
        return send_from_directory('statics/qr', filename=filename, mimetype='image/png')

    except AttributeError:
        return {'error': "Incorrect/Invalid Arguments."}


if __name__ == '__main__':
    img = qrcode.make('some data')
