import json
from uuid import uuid4

import jwt
import qrcode
from PIL import Image
from flask import Blueprint, request, send_from_directory
from jwt import InvalidSignatureError

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
            return None

        return admin_id
    except (InvalidSignatureError, KeyError, ValidationError):
        return None


@admin.route("/code", methods=['GET'])
def generate_code():
    admin_id = authenticate(request)
    if not admin_id:
        return {'error': 'Authentication Failure'}, ValidationError

    restaurant_id = request.args.get('restaurant_id')
    table = request.args.get('table')

    if restaurant_id is None or table is None:
        return {'error': "Incorrect/Invalid Arguments."}, ValidationError
    with connection() as conn, conn.cursor() as cur:
        cur.execute("Select name from restaurant where id = %s && admin_id = %s", (restaurant_id, admin_id,))
        if cur.rowcount == 0:
            return {'error': "Restaurant and Admin Pair doesn't exists."}
        cur.execute("Select * from tables where restaurant_id = %s && name = %s", (restaurant_id, table))
        if cur.rowcount == 0:
            return {'error': "Restaurant and Table Pair doesn't exists."}

    params = {'restaurant_id': restaurant_id, 'table': table}
    qr = qrcode.QRCode(
        version=5,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=15,
        border=4,
    )
    qr.add_data(json.dumps(params))
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")

    logo_display = Image.open('statics/Geek-Lords.jpeg')
    logo_display.thumbnail((120, 120))
    logo_pos = ((image.size[0] - logo_display.size[0]) // 2, (image.size[1] - logo_display.size[1]) // 2)
    image.paste(logo_display, logo_pos)

    # if two people request qr code at almost same time, using the
    # same file will corrupt at least one response
    filename = f'{restaurant_id}-{table}-{uuid4()}.png'
    image.save('statics/qr/' + filename)
    return send_from_directory('statics/qr', filename=filename, mimetype='image/png')


if __name__ == '__main__':
    image = qrcode.make('some data')
