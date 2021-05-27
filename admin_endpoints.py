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
    except (InvalidSignatureError, KeyError, jwt.exceptions.DecodeError):
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


@admin.route('/create_table', methods=['POST'])
def create_table():
    """
    creates a new table:

    Sample input -
    {
        "restaurant_id": "id of restaurant",
        "table": "name of table"
    }

    Sample output -
    {
        "table_id": "<id of table>"
    }

    Sample error -
    {
        "error": "<reason for error>"
    }
    """
    admin_id = authenticate(request)

    if not admin_id:
        return {'error': 'Authentication Failure'}, ValidationError

    if not request.json:
        return {'error': 'No json found'}, ValidationError

    restaurant_id = request.json.get('restaurant_id')
    table = request.json.get('table')

    if not restaurant_id or not table:
        return {'error': 'Invalid input'}, ValidationError

    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            'select name from restaurant '
            'where id = %s and admin_id = %s',
            (restaurant_id, admin_id)
        )

        if cur.rowcount == 0:
            return {'error': 'Restaurant not found'}, ValidationError

        # mysql version deployed on heroku does not support retuning clause
        # so have to use two queries
        cur.execute(
            'insert into tables(name, restaurant_id) values (%s, %s)',
            (table, restaurant_id)
        )

        cur.execute('select last_insert_id()')
        table_id = cur.fetchone()[0]

        return {'table_id': table_id}


@admin.route('/table', methods=['DELETE'])
def delete_table():
    """
    Deletes a table.

    Url - /api/v1/admin/table?id=<id of table to delete>

    Sample output -
    {
        "success": true
    }

    Sample error -
    {
        "error": "reason for error"
    }
    """
    table_id = request.args.get('id')
    if not table_id:
        return {'error': 'Table id not found in request'}, ValidationError

    admin_id = authenticate(request)

    if not admin_id:
        return {'error': 'Authentication failed'}, ValidationError

    with connection() as conn, conn.cursor() as cur:
        cur.execute('select id from orders where table_id = %s', (table_id,))
        if cur.rowcount != 0:
            return {'error': 'Cannot delete this table. Someone has ordered from here.'}, ValidationError

        # we need to check whether the user is the admin of the restaurant
        # whose table they are trying to delete
        restaurant_ids = get_restaurant_ids(admin_id, cur)

        if len(restaurant_ids) == 0:
            return {'error': 'You do not administer any restaurant'}, ValidationError

        cur.execute(
            'delete from tables where id = %s and restaurant_id in %s',
            (table_id, restaurant_ids)
        )

        if cur.rowcount == 0:
            return {'error': 'The table does not exist or you do not own the restaurant'}, ValidationError

        conn.commit()
        return {'success': True}


def get_restaurant_ids(admin_id, cur):
    cur.execute(
        'select id from restaurant where admin_id = %s',
        (admin_id,)
    )
    # cur.fetchall() returns a list of tuples but we want a tuple
    # of restaurant ids.
    #
    # it needs to be tuple because we will need to "in" clause in
    # sql which doesn't work with list
    restaurant_ids = tuple(map(lambda x: x[0], cur.fetchall()))
    return restaurant_ids


@admin.route('/rename_table', methods=['PUT'])
def update_table():
    """
    url - /api/v1/admin/table?id=<id of table>

    Sample input -
    {
        "name": "new name of table"
    }

    Sample output -
    {
        "success": true
    }

    Sample error -
    {
        "error": "reason for error"
    }
    """
    table_id = request.args.get('id')
    if not table_id:
        return {'error': 'Table id not found'}, ValidationError

    if not request.json:
        return {'error': 'No Json data found'}, ValidationError

    new_table_name = request.json.get('name')
    if not new_table_name:
        return {'error': 'New name of table not found'}, ValidationError

    admin_id = authenticate(request)
    if not admin_id:
        return {'error': 'Authentication failed'}, ValidationError

    with connection() as conn, conn.cursor() as cur:
        # we need to check whether the user is the admin of the restaurant
        # whose table they are trying to delete
        restaurant_ids = get_restaurant_ids(admin_id, cur)

        if len(restaurant_ids) == 0:
            return {'error': 'You do not administer any restaurant'}, ValidationError

        cur.execute(
            'update tables set name = %s where id = %s and restaurant_id in %s',
            (new_table_name, table_id, restaurant_ids)
        )

        if cur.rowcount == 0:
            return {'error': 'The table does not exist or you do not own the restaurant'}, ValidationError

        conn.commit()
        return {'success': True}


# unauthenticated route because this information is nothing secret
@admin.route('/all_tables', methods=['GET'])
def get_all_tables():
    """
    url - /api/v1/admin/all_tables?restaurant_id=<id of restaurant>

    sample error -
    {
        "error": "reason for error"
    }

    sample output -
    {
        "tables": [
            {
                "id": 1,
                "name": "table 1"
            },
            {
                "id": 2,
                "name": "table 2"
            },
            {
                "id": 3,
                "name": "table 3"
            }
        ]
    }
    """
    restaurant_id = request.args.get('restaurant_id')

    if not restaurant_id:
        return {'error': 'Restaurant id not found'}, ValidationError

    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            'select id, name from tables where restaurant_id = %s',
            (restaurant_id,)
        )

        return {'tables': list(map(lambda x: {'id': x[0], 'name': x[1]}, cur.fetchall()))}
