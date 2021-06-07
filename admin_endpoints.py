import json
from uuid import uuid4

import bcrypt
import jwt
import pymysql
import qrcode
import requests
from PIL import Image
from email_validator import EmailNotValidError, validate_email
from flask import Blueprint, request, send_from_directory
from jwt import InvalidSignatureError
# from urlvalidator import URLValidator

from config import jwt_secret
from db_utils import connection

admin = Blueprint('admin', __name__)

# HTTP Errors
ValidationError = 401

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
    except (InvalidSignatureError, KeyError, jwt.exceptions.DecodeError):
        return None


@admin.route("/code", methods=['GET'])
def generate_code():
    # admin_id = authenticate(request)
    # if not admin_id:
    #     return {'error': 'Authentication Failure'}, ValidationError

    restaurant_id = request.args.get('restaurant_id')
    table = request.args.get('table')

    if restaurant_id is None or table is None:
        return {'error': "Incorrect/Invalid Arguments."}, ValidationError
    with connection() as conn, conn.cursor() as cur:
        cur.execute("Select name from restaurant where id = %s", (restaurant_id,))
        if cur.rowcount == 0:
            return {'error': "Restaurant and Admin Pair doesn't exists."}

        name = cur.fetchone()[0]

        cur.execute("Select * from tables where restaurant_id = %s and id = %s", (restaurant_id, table))
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
        with open('statics/qr/' + filename, 'rb') as f:
            return f.read(), 200, {'Content-Type': 'image/png', 'Content-Disposition': f'attachment; filename={name}.png'}


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
            return {'error': 'Email Address is not valid'}, ValidationError

        if not contact_number.isdigit() or len(contact_number) != 10:
            return {"error": "Mobile Number is not valid."}
        with connection() as conn, conn.cursor() as cur:
            cur.execute("Select contact_number from admin where contact_number = %s", contact_number)
            if cur.rowcount == 1:
                return {"error": "Mobile Number already exists."}, ValidationError

        password = str(request.json["password"]).strip()

        if len(password) < MinPasswordLength or len(password) > MaxPasswordLength:
            return ({'error': f'password should be between {MinPasswordLength} ' f'and {MaxPasswordLength} characters'},
                    ValidationError)

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
            return {'error': "Credentials already registered with other account. "}, ValidationError

    except KeyError:
        return {'error': 'Invalid input. One or more parameters absent'}, ValidationError
    except pymysql.err.IntegrityError:
        return {'error': 'User already exists'}, ValidationError


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
    """
    admin_id = authenticate(request)

    if not admin_id:
        return {'error': 'Authentication error'}, ValidationError

    with connection() as con, con.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute("Select id,name,photo_url,address from restaurant where admin_id = %s", admin_id)
        return {"restaurant_details": cur.fetchall()}


@admin.route("/add_restaurant", methods=['POST'])
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
        if not admin_id:
            return {"error": "User Authentication Failed."}, ValidationError
        name = request.json['name']
        description = request.json['description']
        photo_url = request.json['photo_url']
        tax_percentage = request.json['tax_percent']
        address = request.json['address']
        pincode = request.json['pincode']

        # Validations
        if len(name) < 3 or len(name) > 60:
            return {"error": "Restaurant Name length should be between 3 to 60 letters."}, ValidationError
        try:
            requests.get(str(photo_url))
        except requests.ConnectionError:
            return {"error": "Photo URL doesn't exist on Internet."}, ValidationError
        try:
            isinstance(float(tax_percentage), float)
        #     Also check if zero
        except ValueError:
            return {"error": "Tax Amounts can't contain any letter or Special Symbols."}
        if len(address) < 10 or len(address) > 100:
            return {"error": "Address is too short. (Minimum 10 Letters) "}, ValidationError
        if len(pincode) != 6 or not pincode.isdigit():
            return {"error": "Invalid Pincode."}, ValidationError
        with connection() as conn, conn.cursor() as cur:
            restaurant_id = uuid4()
            cur.execute(
                "insert into restaurant(id,name,description,photo_url,tax_percent,admin_id,address,pincode) values (%s,%s,%s,%s,%s,%s,%s,%s)",
                (restaurant_id, name, description, photo_url, tax_percentage, admin_id, address, pincode))
            conn.commit()
        return {'restaurant_id': restaurant_id}
    except KeyError:
        return {"error": "Some Credentials are missing."}, ValidationError
    except TypeError:
        return {"error": "Invalid Input"}, ValidationError


@admin.route('/create_table', methods=['POST'])
def create_table():
    """
    creates a new table:

    Headers - X-Auth-Token: <jwt>

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

        conn.commit()

        return {'table_id': table_id}


@admin.route('/table', methods=['DELETE'])
def delete_table():
    """
    Deletes a table.

    Url - /api/v1/admin/table?id=<id of table to delete>
    Headers - X-Auth-Token: <jwt>

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
    Headers - X-Auth-Token: <jwt>

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
    Headers - X-Auth-Token: <jwt>

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


@admin.route("/profile", methods=['GET'])
def get_profile():
    """
        Sample Input:
            send JWTToken from Header with key - "X-Auth-Token"
        Sample Output:
            {
                "admin_information": {
                    "contact_number": "9373496549",
                    "email_address": "mynameissarveshjoshi@gmail.com",
                    "f_name": "Sarvesh",
                    "l_name": "Joshi"
                }
            }
    """

    admin_id = authenticate(request)
    if not admin_id:
        return {"error": "User Authentication failed."}, ValidationError
    with connection() as conn, conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute("SELECT f_name, l_name, email_address, contact_number from admin where id=%s", admin_id)
        if cur.rowcount == 0:
            return {"error": admin_id + "Requested User doesn't exists."}, ValidationError
        user = cur.fetchone()
        return {"admin_information": user}


@admin.route("/profile", methods=['POST'])
def update_profile():
    admin_id = authenticate(request)
    if not admin_id:
        return {"error": "User Authentication Failed"}, ValidationError
    if not request.json:
        return {'error': "No JSON Data found."}, ValidationError

    try:
        f_name = str(request.json["f_name"])
        l_name = str(request.json["l_name"])
        contact = str(request.json["contact_number"])
        email_address = str(request.json["email_address"])
        if 1 > len(f_name) or len(f_name) > 50 or 1 > len(l_name) or len(l_name) > 50:
            return {"error": "Length of Name fields should be between 1 and 50."}, ValidationError
        if not contact.isdigit() or len(contact) != 10:
            return {"error": "Mobile Number is not valid."}
        try:
            # validating email and assigning the valid email back to email
            email_id = validate_email(email_address).email
            with connection() as conn, conn.cursor() as cur:
                cur.execute("select * from admin where id = %s", admin_id)
                if cur.rowcount < 1:
                    return {"error": "Requested User Doesn't Exists"}, ValidationError
                cur.execute(
                    "update admin set f_name = %s, l_name = %s,email_address = %s, contact_number = %s where id = %s",
                    (f_name, l_name, email_id, contact, admin_id))
                conn.commit()
            return {"success": 'success'}, 200
        except EmailNotValidError:
            return {'error': 'Email Address is not valid'}, ValidationError
        except pymysql.err.IntegrityError:
            return {'error': "Email/Contact Number already registered with other account."}, ValidationError
        except pymysql.InternalError:
            return {"error": "User doesn't exists."}, ValidationError
    except KeyError:
        return {"error": "Invalid Credentials"}, ValidationError


@admin.route("/get_menus", methods=['GET'])
def get_menus():
    """
        header: X-Auth-Token: <jwt>
        url - /api/v1/admin/get_menus?restaurant_id=<id>

        Sample Output:
            {
            "menu": [
                {
                    "description": "Express Inn's Speciality. Main Course/Indian",
                    "id": 1,
                    "name": "Paneer Butter Masala",
                    "photo_url": "paneerbuttermasala.jpg",
                    "price": 480.00
                },
                {
                    "description": "Express Inn's Speciality. Main Course/Indian",
                    "id": 2,
                    "name": "Kadhai Paneer",
                    "photo_url": "paneer-kadhai.jpg",
                    "price": 460.00
                }
                    ]
            }
    """
    try:
        admin_id = authenticate(request)
        if not admin_id:
            print('Authentication failed')
            return {"error": "User Authentication failed"}, ValidationError

        restaurant_id = request.args['restaurant_id']

        with connection() as conn, conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute("Select admin_id from restaurant where id = %s", restaurant_id)
            if cur.rowcount == 0 or cur.fetchone()['admin_id'] != admin_id:
                print('Authorization failed')
                return {"error": "Authorization failed"}, ValidationError

            cur.execute(
                "Select id, name, description, photo_url ,price from menu "
                "where (restaurant_id = %s AND active_menu = 0)",
                restaurant_id
            )
            menus = cur.fetchall()
            for menu in menus:
                menu['price'] = float(menu['price'])
        return {"menu": menus}
    except KeyError:
        print('missing restaurant id')
        return {"error": "Missing Restaurant Id."}, ValidationError
    except TypeError as e:
        print(e)
        return {"error": "Invalid Information"}, ValidationError


@admin.route("/new_menu", methods=["POST"])
def new_menu():
    """
        Sample Input: JWT Token in Header
        {
            "name":"Name",
            "description":"Desc",
            "photo":"Photo.jpeg",
            "price":20,
            "restaurant_id":"ID"
        }
        Sample Output:
        {
            'success': "New Menu Successfully added."
        }
    """
    try:
        if not request.json:
            return {"error": "JSON Data not found."}, ValidationError
        admin_id = authenticate(request)
        menu_desc = str(request.json["description"])
        menu_photo = request.json["photo"]
        menu_name = str(request.json["name"])
        menu_price = str(request.json["price"])
        restaurant_id = request.json["restaurant_id"]
        if not admin_id:
            return {"error": "User Authentication Failed."}, ValidationError
        if len(menu_name) < 3 or len(menu_name) > 50:
            return {"error", "Name of Food Item must'be of length between 3 and 50."}, ValidationError
        if not menu_price.isdigit():
            return {"error": "Price should be in digit."}, ValidationError
        with connection() as conn, conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute("Select admin_id from restaurant where id = %s", restaurant_id)
            if not cur.fetchone()['admin_id'] == admin_id:
                return {"error": "Restaurant and Requesting Admin Pair doesn't exists."}, ValidationError
            cur.execute(
                "insert into menu(name, description, photo_url, restaurant_id, price) values (%s,%s,%s,%s,%s)",
                (menu_name, menu_desc, menu_photo, restaurant_id, menu_price))
            cur.execute('select last_insert_id()')
            row = cur.fetchone()
            menu_id = row['last_insert_id()']
            conn.commit()
        return {'success': "New Menu Successfully added.", 'menu_id': menu_id}
    except KeyError:
        return {"error": "Important Information Missing "}, ValidationError
    except TypeError:
        return {"error": "Invalid Information"}, ValidationError


@admin.route("/delete_menu", methods=["POST"])
def delete_menu():
    """
        Sample Input: UserID in Header
            {
                "menu_id":<menu_id>
            }
        Sample Output:
            {
                "success": "Successfully Deleted the Menu."
            }
    """
    if not request.json:
        return {"error": "JSON Data not found."}, ValidationError
    admin_id = authenticate(request)
    if not admin_id:
        return {"error": "Authentication Failed"}, ValidationError
    try:
        menu_id = request.json['menu_id']
        with connection() as conn, conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(
                "Select restaurant.admin_id from restaurant inner join menu on restaurant.id = menu.restaurant_id where menu.id = %s",
                menu_id)
            if not admin_id == cur.fetchone()['admin_id']:
                return {"error": "Requesting Admin and Menu Pair doesn't exists."}, ValidationError
            cur.execute(
                "Select orders.table_id from orders inner join order_items on orders.id = order_items.order_id where (order_items.menu_id = %s and orders.payment_status <> 0)",
                menu_id)
            if cur.rowcount > 0:
                return {
                           "error": "Unable to Delete Item as Customers are still ordering it. Please try again later."}, ValidationError
            cur.execute("update menu set active_menu = 1 where id = %s", menu_id)
            conn.commit()
            return {"success": "Successfully Deleted the Menu."}
    except KeyError:
        return {"error": "Some Fields Missing"}, ValidationError
    except TypeError:
        return {"error": "Invalid Request"}, ValidationError


@admin.route("/order_history", methods=["GET"])
def order_history():
    try:
        admin_id = authenticate(request)
        if not admin_id:
            return {"error": "User Authentication Failed."}, ValidationError
        if not request.json:
            return {'error': "JSON Data not Found."}, ValidationError
        restaurant_id = request.json["restaurant_id"]
        with connection() as conn, conn.cursor(pymysql.cursors.DictCursor) as curr:
            curr.execute("Select admin_id from restaurant where id=%s", restaurant_id)
            if not admin_id == curr.fetchone()['admin_id']:
                return {"error": "Requesting Admin and Menu Pair doesn't exists."}, ValidationError
            curr.execute(
                "Select orders.id, orders.price_excluding_tax, orders.tax, orders.time_and_date, users.name from orders join restaurant on orders.restaurant_id = restaurant.id join users on users.id = orders.user_id where (restaurant.id = %s and orders.payment_status = 0)",
                restaurant_id)
            return {"order_history": curr.fetchall()}
    except KeyError:
        return {"error": "Restaurant ID not found"}, ValidationError
    except TypeError:
        return {"error": "Invalid input"}, ValidationError


@admin.route("/detailed_order/<order_id>", )
def detailed_order(order_id):
    try:
        admin_id = authenticate(request)
        if not admin_id:
            return {"error": "User Authentication Failed."}, ValidationError
        with connection() as conn, conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(
                "Select restaurant.admin_id from restaurant join orders on restaurant.id = orders.restaurant_id where orders.id = %s ",
                order_id)
            if admin_id != cur.fetchone()['admin_id']:
                return {"error": "Unauthorized Request"}, ValidationError
            cur.execute(
                "Select users.name, orders.time_and_date,orders.price_excluding_tax, orders.tax from users join orders on orders.user_id = users.id where orders.id = %s",
                order_id)
            overall_information = cur.fetchone()
            cur.execute(
                "Select menu.name, menu.price, order_items.quantity from menu join order_items on menu.id = order_items.menu_id where order_items.order_id = %s ",
                order_id)
            detailed_bill = cur.fetchall()
            return {"details": {"overall_information": overall_information, "bill": detailed_bill}}
    except KeyError:
        return {"error": "Invalid Input"}, ValidationError
    except TypeError:
        return {"error": "Invalid Request for Order Details."}, ValidationError


@admin.route("/new_orders", methods=["GET"])
def new_orders():
    try:
        admin_id = authenticate(request)
        if not admin_id:
            return {"error": "User Authentication Failed"}, ValidationError
        if not request.json:
            return {"error": "JSON Data not found."}, ValidationError
        restaurant_id = request.json["restaurant_id"]
        with connection() as conn, conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute("Select admin_id from restaurant where id = %s", restaurant_id)
            if cur.fetchone()['admin_id'] != admin_id:
                return {"error": "Unauthorized Request."}, ValidationError
            cur.execute(
                "Select new_orders.id, menu.name, menu.description, new_orders.quantity, orders.table_id, users.name from new_orders join menu on new_orders.menu_id = menu.id join orders on orders.id = new_orders.order_id join users on orders.user_id = users.id where (orders.restaurant_id = %s and new_orders.delivered_items = 1) order by orders.time_and_date asc",
                restaurant_id)
            yet_to_deliver = cur.fetchall()
            return {"new_orders": yet_to_deliver}
    except KeyError:
        return {"error": "Important Data is missing."}, ValidationError
    except TypeError:
        return {"error": "Invalid Inputs."}, ValidationError


@admin.route("/delivered/<id>", methods=["POST"])
def delivered_menu(id):
    try:
        admin_id = authenticate(request)
        restaurant_id = request.json['restaurant_id']
        if not request.json:
            return {"error": "JSON Data is missing"}, ValidationError
        if not admin:
            return {"error": "Admin Authentication Failed."}, ValidationError
        with connection() as conn, conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(
                "Select admin_id from restaurant where id = %s",
                restaurant_id)
            if admin_id != cur.fetchone()['admin_id']:
                return {"error": "Unauthorized Request."}, ValidationError
            cur.execute("update new_orders set delivered_items = 0 where id = %s", id)
            conn.commit()
            return {"success": "Successfully Delivered Requested Item"}, 200
    except TypeError:
        return {"error", "Invalid Inputs"}, ValidationError
    except KeyError:
        return {"error": "JSON Data missing."}, ValidationError


@admin.route("/recent_orders", methods=["POST"])
def recent_orders():
    try:
        admin_id = authenticate(request)
        if not request.json:
            return {"error", "JSON Data is missing."}, ValidationError
        if not admin_id:
            return {"error": "Admin Authentication Failed."}, ValidationError
        restaurant_id = request.json['restaurant_id']
        with connection() as conn, conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute("Select admin_id from restaurant where id = %s", restaurant_id)
            if cur.fetchone()['admin_id'] != admin_id:
                return {"error": "Unauthorised Request."}, ValidationError
            cur.execute(
                "Select new_orders.quantity,tables.name, orders.payment_status, orders.time_and_date, users.name, menu.name from new_orders join orders on new_orders.order_id = orders.id join users on users.id = orders.user_id join menu on menu.id = new_orders.menu_id join tables on orders.table_id =  tables.id where (new_orders.delivered_items = 0  and orders.restaurant_id = %s and orders.time_and_date > DATE_SUB(CURDATE(), INTERVAL 1 DAY)) order by orders.time_and_date asc",
                restaurant_id)
            return {"recent_orders": cur.fetchall()}
    except TypeError:
        return {"error": "Invalid Input"}, ValidationError
    except KeyError:
        return {"error": "Required JSON Data Missing"}, ValidationError
