from uuid import uuid4

import bcrypt
import jwt
import pymysql
from email_validator import EmailNotValidError, validate_email
from flask import Blueprint, request
from jwt import InvalidSignatureError

from config import jwt_secret
from db_utils import connection

MinPasswordLength = 5

user = Blueprint('user', __name__)

# HTTP error code for validation error
ValidationError = 422

MaxPasswordLength = 70


class order:
    def __init__(self, order_id, menu_id, quantity):
        self.order_id = order_id
        self.menu_id = menu_id
        self.quantity = int(quantity)

    def set_price(self):
        try:
            with connection() as conn, conn.cursor() as cur:
                cur.execute("select price from menu where id = %s", (self.menu_id,))
                self.price = float(cur.fetchone()[0]) * self.quantity
                return self.price
        except TypeError:
            return TypeError

    def validate_request(self):
        if self.order_id is None or self.menu_id is None or self.quantity is None or self.quantity <= 0:
            raise ValidationError

    def get_restaurant(self):
        try:
            with connection() as conn, conn.cursor() as cur:
                cur.execute("select restaurant_id from menu where id = %s", (self.menu_id,))
                restaurant_id = cur.fetchone()[0]
                return restaurant_id
        except TypeError:
            return TypeError

    def set_order(self):
        try:
            with connection() as conn, conn.cursor() as cur:
                restaurant = self.get_restaurant()
                cur.execute("select tax from restaurant where id = %s", (restaurant,))
                self.tax = float(cur.fetchone()[0])
                cur.execute("insert into order_items values(%s, %s, %s, %s, %s) on duplicate key "
                            "update quantity = quantity + %s, price = price + %s ",
                            (self.order_id, self.menu_id, self.quantity, self.price, self.tax, int(self.quantity),
                             float(self.price)))
                conn.commit()
                return {"message": "Order Placed"}, 200
                # insert into hotels_table values(10, 11, 6, 60) on duplicate key update quantity = quantity + 6, price = price + 60;
        except TypeError as t:
            print(t)
            return TypeError


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def password_valid(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))


@user.route('/create_user', methods=['POST'])
def create_user():
    """
    Creates user with name, email and password
    
    Name must not be empty, email must be a valid email and password
    must be between ${MinPasswordLength} and ${MaxPasswordLength}
    
    Sample input - 
    {
        "name": "Hemil",
        "password": "abcdef",
        "email": "abc@def.com"
    }
    
    Sample output - 
    {
        "jwt_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiNWQ4NDFlNzMtZmRmNS00YmRlLTk1YjQtMWQzMWU0MDUxNzQ4In0.2nQA-voqYvUadLefIKLxPplWUQTIhqOS_iVfMNj62oE"
    }

    Sample error -
    {
        "error": "reason for error"
    }
    :return: a jwt token
    """
    try:
        if not request.json:
            return {'error': 'No json data found'}, ValidationError

        name = str(request.json['name'])

        if len(name) == 0:
            return {'error': 'name invalid or empty'}, ValidationError

        password = str(request.json['password'])

        if len(password) < MinPasswordLength or len(password) > MaxPasswordLength:
            return (
                {
                    'error': f'password should be between {MinPasswordLength} '
                             f'and {MaxPasswordLength} characters'
                },
                ValidationError
            )

        email = str(request.json['email'])
        try:
            # validating email and assigning the valid email back to email
            email = validate_email(email).email
        except EmailNotValidError:
            return {'error': 'email is not valid'}

        with connection() as conn, conn.cursor() as cur:
            user_id = str(uuid4())
            cur.execute(
                'insert into users values(%s, %s, %s, %s)',
                (user_id, name, email, hash_password(password)),
            )
            conn.commit()

            jwt_token = jwt.encode({'user_id': user_id}, jwt_secret, algorithm='HS256')

            return {
                'jwt_token': jwt_token,
            }
    except KeyError:
        return {'error': 'Invalid input. One or more parameters absent'}, ValidationError
    except pymysql.err.IntegrityError:
        return {'error': 'User already exists'}


@user.route('/authenticate', methods=['POST'])
def authenticate():
    """
    Takes email and password string and returns a jwt token is user
    is found. Else returns the error

    Sample input -
    {
        "password": "abcdef",
        "email": "abc@def.com"
    }

    Sample output -
    {
        "jwt_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiNWQ4NDFlNzMtZmRmNS00YmRlLTk1YjQtMWQzMWU0MDUxNzQ4In0.2nQA-voqYvUadLefIKLxPplWUQTIhqOS_iVfMNj62oE"
    }

    Sample error -
    {
        "error": "reason for error"
    }
    :return:
    """
    try:
        if not request.json:
            return {'error': 'No json data found'}, ValidationError

        email = str(request.json['email'])
        password = str(request.json['password'])

        if len(password) < MinPasswordLength or len(password) > MaxPasswordLength:
            return (
                {
                    'error': f'password should be between {MinPasswordLength} '
                             f'and {MaxPasswordLength} characters'
                },
                ValidationError
            )

        try:
            # validating email and assigning the valid email back to email
            email = validate_email(email).email
        except EmailNotValidError:
            return {'error': 'email is not valid'}

        with connection() as conn, conn.cursor() as cur:
            cur.execute(
                'select id, password_hash from users where email = %s',
                # execute needs a tuple of parameters. comma converts
                # (email) into a tuple containing one element - email
                (email,),
            )

            if cur.rowcount == 0:
                return {'error': 'Invalid email or password'}

            row = cur.fetchone()
            user_id = row[0]
            hashed_password = row[1]

            if password_valid(password, hashed_password):
                jwt_token = jwt.encode({'user_id': user_id}, jwt_secret, algorithm='HS256')

                return {
                    'jwt_token': jwt_token,
                }

            # if password is not valid
            return {'error': 'Invalid email or password'}
    except KeyError:
        return {'error': 'Invalid input. One or more parameters absent'}, ValidationError


# temporary
@user.route('/validate_token')
def validate_token():
    user_id = jwt.decode(request.json['jwt'], jwt_secret, algorithms=['HS256'])['user_id']
    return {'token': user_id}


# decodes user id. In case of error, returns None
def _decoded_user_id(_request):
    try:
        return jwt.decode(_request.headers['X-Auth-Token'], jwt_secret, algorithms=['HS256'])['user_id']
    except InvalidSignatureError:
        return None
    except KeyError:
        return None


@user.route('/menu')
def get_menu():
    restaurant_id = request.args.get('restaurant_id', None)
    table_no = request.args.get('table_no', None)

    if not restaurant_id or not table_no:
        return {'error': 'Invalid input. One or more parameters absent'}


@user.route("/order", methods=["POST"])
def create_order():
    try:
        order_id = str(uuid4())
        user_id = _decoded_user_id(request)
        with connection() as conn, conn.cursor() as cur:
            cur.execute("insert into orders values(%s,%s)", (order_id, user_id), )
            conn.commit()
            return {'order_id': order_id}
    except KeyError:
        return {'error': 'Invalid input. One or more parameters absent'}, ValidationError


@user.route("/order_items", methods=["POST"])
def order_items():
    try:
        if not request.json:
            return {'error': 'No json data found'}, ValidationError
        order_id = request.json["order_id"]
        order_list = request.json["order_list"]
        list_of_orders = []
        for orders in order_list:
            list_of_orders.append(order(order_id, orders.get("menu_id"), orders.get("quantity")))
        restaurant_id = list_of_orders[0].get_restaurant()
        for element in list_of_orders:
            try:
                restaurant = element.get_restaurant()
                price = element.set_price()
                if element.validate_request() is not None or restaurant is TypeError or price is TypeError:
                    raise TypeError
                if restaurant_id != restaurant:
                    raise AttributeError
            except TypeError:
                return {"error": "Query had some Invalid Inputs."}, ValidationError
            except AttributeError:
                return {"error": "Food Orders are from different restaurants"}, ValidationError
        for element in list_of_orders:
            try:
                if element.set_order() is TypeError:
                    raise TypeError
            except TypeError:
                return {"error": "Order wasn't placed because of Bad Credentials."}, ValidationError
        return {"message": "request accepted."}, 200
    except KeyError:
        return {'error': 'Invalid input. One or more parameters absent'}, ValidationError
