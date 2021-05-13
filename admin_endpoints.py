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


@admin.route("/create_admin", methods=['POST'])
def create_admin():
    """
    How to create a new admin account? 
        Name can be anything except empty, Email should be a actual Email and Unique and Phone Number should be a actual 
        Phone Number and Unique, Password can be anything with length in between 8 to 70.
            Sample JSON Input:
                {
                    "name":"Sarvesh Joshi",
                    "email_id":"fake@gmail.com",
                    "password":"anyPassword",
                    "phone":"9876543210"
                }
            Sample JSON Output:
                {
                     "jwt_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiNWQ4NDFlNzMtZmRmNS00YmRlLTk1YjQtMWQzMWU0MDUxNzQ4In0.2nQA-voqYvUadLefIKLxPplWUQTIhqOS_iVfMNj62oE"
                }
            i.e. returns a JWT Token as a success, else an error.
        
    """
    try:
        if not request.json:
            return {"error": "No JSON Data found."}, ValidationError
        name = str(request.json['name'])
        email = str(request.json['email_id'])
        password = str(request.json['password'])
        phone = str(request.json['phone'])
        if name is None or len(name) == 0:
            return {"error": "Invalid  Name"}, ValidationError

        try:
            email = validate_email(email).email
        except EmailNotValidError:
            return {'error': "Invalid Email Address."}, ValidationError

        if len(password) < 6 or len(password) > 70:
            return {"error": "Length of Password should be between 6 to 70."}, ValidationError
        hashed_password = hash_password(password)

        if not phone.isdigit() or len(phone) != 10:
            return {"error": "Invalid Phone Number."}, ValidationError
        user_id = str(uuid4())
        with connection() as conn, conn.cursor() as cur:
            cur.execute(
                "Insert into admins(id, name, hashed_password, email_id, phone) values(%s,%s,%s,%s,%s)",
                (user_id, name, hashed_password, email, phone)
            )
            conn.commit()
            jwt_token = jwt.encode({'user_id': user_id, 'is_admin': True}, jwt_secret, algorithm='HS256')
            # Added is_admin field here because we're checking it for Authentication in other places.
        return {
            "jwt_token": jwt_token
        }

    except KeyError:
        return {"error": "One or more parameters absent."}
    except pymysql.err.IntegrityError:
        return {"error": "Contact Information already exists."}


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
    image = qrcode.make('some data')
