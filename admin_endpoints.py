import io

import jwt
import qrcode
from flask import Blueprint, request
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
        admin_id = jwt.decode(_requests.headers['X-Auth-Token'], jwt_secret, algorithms=['HS256'])['user_id']
        is_admin = jwt.decode(_requests.headers['X-Auth-Token'], jwt_secret, algorithms=['HS256'])['is_admin']
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
        table_id = request.args.get('table_id')
        if admin_id is None or restaurant_id is None or table_id is None:
            raise TypeError
        with connection() as conn, conn.cursor() as cur:
            cur.execute("Select name from restaurant where id = %s && admin_id = %s", (restaurant_id, admin_id,))
            if cur.rowcount == 0:
                return {'error': "Restaurant and Admin Pair doesn't exists."}
            cur.execute("Select * from tables where restaurant_id = %s && name = %s", (restaurant_id, table_id))
            if cur.rowcount == 0:
                return {'error': "Restaurant and Table Pair doesn't exists."}
        qr = qrcode.QRCode(version=5, error_correction=qrcode.constants.ERROR_CORRECT_H,
                           box_size=15,
                           border=4, )

        qr.add_data("http://localhost:5000/api/v1/menu?restaurant_id=%s&table_id=%s".format(restaurant_id, table_id))
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
        # logo_display = Image.open('statics/Geek-Lords.jpeg')
        # logo_display.thumbnail((120, 120))
        # logo_pos = ((img.size[0] - logo_display.size[0]) // 2, (img.size[1] - logo_display.size[1]) // 2)
        # img.paste(logo_display, logo_pos)

        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr)

        return {"qr_code": img_byte_arr.getvalue()}

    except AttributeError:
        return {'error': "Incorrect/Invalid Arguments."}


if __name__ == '__main__':
    img = qrcode.make('some data')
