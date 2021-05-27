import json
from uuid import uuid4
from user_endpoints import hash_password
import jwt
import qrcode
from PIL import Image
from flask import Blueprint, request, send_from_directory
from jwt import InvalidSignatureError
from email_validator import EmailNotValidError, validate_email
from config import jwt_secret
from db_utils import connection
import pymysql
import re

admin = Blueprint('admin', __name__)

# HTTP Errors
ValidationError = 422

MinPasswordLength = 5

MaxPasswordLength = 70


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
        cur.execute("Select * from tables where restaurant_id = %s && id = %s", (restaurant_id, table))
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


@admin.route("/create_admin", methods=['POST'])
def create_admin():
    try:
        if not request.json:
            return {"error": "Invalid Request for Account Creation."}, ValidationError

        f_name = str(request.json['f_name'])
        l_name = str(request.json['l_name'])
        email_id = str(request.json['email_id'])
        contact_number = str(request.json['contact']).strip()
        password = str(request.json["password"]).strip()

        if 1 > len(f_name) or len(f_name) > 50 or 1 > len(l_name) or len(l_name) > 50:
            return {"error": "Length of Name fields should be between 1 and 50."}, ValidationError

        try:
            # validating email and assigning the valid email back to email
            email_id = validate_email(email_id).email
            with connection() as conn, conn.cursor() as cur:
                cur.execute("select email_address from admin where email_address = %s", email_id)
                if cur.rowcount() == 1:
                    return {"error": "Email Address already exists."}, ValidationError
        except EmailNotValidError:
            return {'error': 'Email Address is not valid'}

        pattern = re.compile("[7-9][0-9]{9}")

        if not pattern.match(contact_number):
            return {"error": "Mobile Number is not valid."}
        with connection() as conn, conn.cursor() as cur:
            cur.execute("Select contact_number from admin where contact_number = %s", contact_number)
            if cur.rowcount() == 1:
                return {"error": "Mobile Number already exists."}, ValidationError

        password = str(request.json['password'])

        if len(password) < MinPasswordLength or len(password) > MaxPasswordLength:
            return {
                       'error': f'password should be between {MinPasswordLength} ' f'and {MaxPasswordLength} characters'}, ValidationError


    except KeyError:
        return {'error': 'Invalid input. One or more parameters absent'}, ValidationError
    except pymysql.err.IntegrityError:
        return {'error': 'User already exists'}


@admin.route("/authenticate_admin", methods=['POST'])
def authenticate_user():
    """
        This function is about authenticating if admin trying to log-in is valid/exists or not.
        Sample Input:   {
                            "email":"real@gmail.com",
                            "password":"anyValidPassword"
                        }
        Sample Output:  {
                            "jwt_token":"eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiNWQ4NDFlNzMtZmRmNS00YmRlLTk1YjQtMWQzMWU0MDUxNzQ4In0.2nQA-voqYvUadLefIKLxPplWUQTIhqOS_iVfMNj62oE"
                        }
    """


if __name__ == '__main__':
    pass
