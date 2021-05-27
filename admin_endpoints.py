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
import bcrypt
import requests

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


def password_valid(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))


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

    logo_display = Image.open('statics/qr/Geek-Lords.jpeg')
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
        Sample Input:
            {
                "f_name":"Sarvesh",
                "l_name":"Joshi",
                "email_id":"mynameissarveshjoshi@gmail.com",
                "contact":"9988776655",
                "password":"anyValidPassword"
            }
        Sample Output:
           {
            'jwt_token': "wowAJWTToken"
           }
           or, Error with Description.
    """
    try:
        if not request.json:
            return {"error": "Invalid Request for Account Creation."}, ValidationError

        f_name = str(request.json['f_name'])
        l_name = str(request.json['l_name'])
        email_id = str(request.json['email_id'])
        contact_number = str(request.json['contact']).strip()

        if 1 > len(f_name) or len(f_name) > 50 or 1 > len(l_name) or len(l_name) > 50:
            return {"error": "Length of Name fields should be between 1 and 50."}, ValidationError

        try:
            # validating email and assigning the valid email back to email
            email_id = validate_email(email_id).email
            with connection() as conn, conn.cursor() as cur:
                cur.execute("select email_address from admin where email_address = %s", email_id)
                if cur.rowcount == 1:
                    return {"error": "Email Address already exists."}, ValidationError
        except EmailNotValidError:
            return {'error': 'Email Address is not valid'}

        if not contact_number.isdigit() or len(contact_number) != 10:
            return {"error": "Mobile Number is not valid."}
        with connection() as conn, conn.cursor() as cur:
            cur.execute("Select contact_number from admin where contact_number = %s", contact_number)
            if cur.rowcount == 1:
                return {"error": "Mobile Number already exists."}, ValidationError

        password = str(request.json["password"]).strip()

        if len(password) < MinPasswordLength or len(password) > MaxPasswordLength:
            return {
                       'error': f'password should be between {MinPasswordLength} ' f'and {MaxPasswordLength} characters'}, ValidationError

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        try:
            with connection() as conn, conn.cursor() as cur:
                admin_id = str(uuid4())
                cur.execute(
                    "insert into admin(id,f_name,l_name,email_address,contact_number,password) values(%s,%s,%s,%s,%s,%s) ",
                    (admin_id, f_name, l_name, email_id, contact_number, hashed_password))
                conn.commit()
            jwt_token = jwt.encode({"user_id": admin_id, "is_admin": True}, jwt_secret, algorithm='HS256')
            return {'jwt_token': jwt_token}
        except pymysql.IntegrityError:
            return {'error': "Credentials already registered with other account. "}

    except KeyError:
        return {'error': 'Invalid input. One or more parameters absent'}, ValidationError
    except pymysql.err.IntegrityError:
        return {'error': 'User already exists'}


@admin.route("/authenticate", methods=['POST'])
def authenticate_user():
    """
        This function is about authenticating if admin trying to log-in is valid/exists or not.
        Sample Input:   {
                            "email":"mynameissarveshjoshi@gmail.com",
                            "password":"anyValidPassword"
}
        Sample Output:  {
                            "jwt_token":"wowAJWTToken"
                        }
    """
    try:
        if not request.json:
            return {"error": "No JSON Data found"}, ValidationError
        email = str(request.json["email"]).strip()
        password = str(request.json['password']).strip()
        with connection() as conn, conn.cursor() as cur:
            cur.execute("Select id, password from admin where email_address = %s", email)
            if cur.rowcount == 0:
                return {"error": "Invalid Email Address/ Email doesn't exists."}

            row = cur.fetchone()
            hashed_password = row[1]
            user_id = row[0]
            if password_valid(password, hashed_password):
                jwt_token = jwt.encode({'user_id': user_id, "is_admin": True}, jwt_secret, algorithm='HS256')
                return {"jwt": jwt_token}
            return {"error": "Email and Password doesn't match."}

    except KeyError:
        return {"error": "Some Credentials Missing."}, ValidationError


@admin.route("/get_restaurant", methods=["GET"])
def get_restaurant():
    """
        Sample Output:
            {
                "restaurant details": {
                    "restaurant details": [
                        {
                                "address": "Pathardi Phata, Mumbai Agra Road, Ambad, Nashik, Maharashtra, India",
                                "id": "1",
                                "name": "Express Inn",
                                "photo_url": "https://www.travelandleisureindia.in/wp-content/uploads/2019/12/Express-inn-feature-2.jpg"
                            },
                            {
                                "address": "Pathardi Phata, Mumbai Agra Road, Ambad, Nashik, Maharashtra, India",
                                "id": "2",
                                "name": "The Gateway Taj - Nashik",
                                "photo_url": "https://i1.wp.com/delectablereveries.com/wp-content/uploads/2017/08/20986518_10155435243471183_707459594_n.jpg?fit=960%2C639&ssl=1"
                            },
                            {
                                "address": "2014 Forest Hills Drive, Frieghville, North Carolina, USA",
                                "id": "4a890455-0e70-4345-8aa9-fd2cc40d5d8f",
                                "name": "Youngsimba's Den",
                                "photo_url": "https://ratcreek.org/wp-content/uploads/2018/07/IMG-1-NewAveBusinessesLaunch-AydanDunniganVickruck-1536x1024.jpg"
                            }
                        ]
                        }
                    }
    """
    admin_id = authenticate(request)
    with connection() as con, con.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute("Select id,name,photo_url,address from restaurant where admin_id = %s", admin_id)
        return {"restaurant details": cur.fetchall()}


@admin.route("/add_restaurant", methods=['GET'])
def add_restaurant():

    """
        Sample Input :
            {
                "name":"Wow a Restaurant",
                "description":"Very Very, Very Very, Very good restaurant!",
                "photo_url":"https://www.google.com/cool-restaurant.jpg",
                "tax_percent":"25.8",
                "address":"Very Cool Street, Behind Famous Monument, Cool City",
                "pincode":"987654"
            }
        Sample Output:
            {
                'restaurant_id': "restaurant_id_lol_"
            }
            or,
            {
                "error":"You made a mistake buddy"
            }
    """
    if not request.json:
        return {"error": "No JSON Data found."}, ValidationError
    try:
        admin_id = authenticate(request)
        name = request.json['name']
        description = request.json['description']
        photo_url = request.json['photo_url']
        tax_percentage = request.json['tax_percent']
        address = request.json['address']
        pincode = request.json['pincode']

        # Validations
        if len(name) < 3 or len(name) > 60:
            return {"error": "Restaurant Name length should be between 3 to 60 letters."}
        try:
            request.get(str(photo_url))
        except requests.ConnectionError:
            return {"error": "Photo URL doesn't exist on Internet."}
        try:
            isinstance(float(tax_percentage), float)
        except ValueError:
            return {"error": "Tax Amounts can't contain any letter or Special Symbols."}
        if len(address) < 10 or len(address) > 100:
            return {"error": "Address is too short. (Minimum 10 Letters) "}
        if len(pincode) != 6 or not pincode.isdigit():
            return {"error": "Invalid Pincode."}
        with connection() as conn, conn.cursor() as cur:
            restaurant_id = uuid4()
            cur.execute(
                "insert into restaurant(id,name,description,photo_url,tax_percent,admin_id,address,pincode) values (%s,%s,%s,%s,%s,%s,%s,%s)",
                (restaurant_id, name, description, photo_url, tax_percentage, admin_id, address, pincode))
            conn.commit()
        return {'restaurant_id': restaurant_id}
    except KeyError:
        return {"error": "Some Credentials are missing."}


if __name__ == '__main__':
    pass
