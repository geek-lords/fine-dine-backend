from uuid import uuid4

import bcrypt
import jwt
import pymysql
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from email_validator import EmailNotValidError, validate_email
from flask import Blueprint, request
from jwt import InvalidSignatureError

import paytm
from config import jwt_secret
from db_utils import connection

MinPasswordLength = 5

user = Blueprint('user', __name__)

scheduler = BackgroundScheduler()


def keep_server_alive():
    requests.get(
        'https://fine-dine-backend.herokuapp.com/api/v1/menu?restaurant_id=6902d892-4d75-44fe-85bd-b92a60260f70'
    )
    print('request sent')


scheduler.add_job(
    keep_server_alive,
    'interval',
    minutes=25,
)

scheduler.start()

# HTTP error code for validation error
ValidationError = 422

MaxPasswordLength = 70


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
        user_id = _decoded_user_id(request)
        if not user_id:
            return {'error': 'Authentication failure'}, ValidationError

        table_name = request.args.get('table')
        if not table_name:
            return {'error': 'table parameter not found in request'}, ValidationError

        restaurant_id = request.args.get('restaurant_id')
        if not restaurant_id:
            return {'error': 'restaurant id not found'}, ValidationError

        with connection() as conn, conn.cursor() as cur:
            cur.execute(
                'select name from restaurant where id = %s',
                (restaurant_id,)
            )

            if cur.rowcount == 0:
                return {'error': 'Restaurant id does not exist'}, ValidationError

            cur.execute(
                'select name from tables '
                'where restaurant_id = %s and name = %s',
                (restaurant_id, table_name)
            )

            if cur.rowcount == 0:
                return {'error': 'Table not found'}, ValidationError

            order_id = str(uuid4())

            cur.execute(
                "insert into orders(id, user_id, table_name, restaurant_id, payment_status) "
                "values(%s, %s, %s, %s, %s)",
                (order_id, user_id, table_name, restaurant_id, paytm.PaymentStatus.NOT_PAID),
            )

            conn.commit()
        return {'order_id': order_id}
    except KeyError:
        return {'error': 'Invalid input. One or more parameters absent'}, ValidationError


@user.route('/checkout', methods=['POST'])
def checkout():
    order_id = request.args.get('order_id')
    if not order_id:
        return {'error': 'Order id not found'}

    user_id = _decoded_user_id(request)
    if not user_id:
        return {'error': 'Authentication failure'}, ValidationError

    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            'select user_id, payment_status, restaurant_id from orders '
            'where id = %s',
            (order_id,)
        )

        if cur.rowcount == 0:
            return {'error': 'Invalid input. Order id does not exist'}, ValidationError

        row = cur.fetchone()
        user_id_who_created_the_order = row[0]
        payment_status = row[1]
        restaurant_id = row[2]

        if user_id != user_id_who_created_the_order:
            return {'error': 'Authentication failure'}, ValidationError

        if payment_status == paytm.PaymentStatus.SUCCESSFUL.value:
            return {'error': 'Order has already been paid'}, ValidationError

        cur.execute(
            'select sum(price) from order_items where order_id = %s',
            (order_id,)
        )

        price = cur.fetchone()[0]
        # sum should return 0 for empty list. But it is somehow returning None
        if price == 0 or price is None:
            return {'error': 'Please book something before checking out'}, ValidationError

        cur.execute(
            'select tax_percent from restaurant where id = %s',
            (restaurant_id,)
        )

        tax_percent = cur.fetchone()[0]
        tax = price * tax_percent / 100
        total_price = price + tax

        cur.execute(
            'update orders set price_excluding_tax = %s, tax = %s where id = %s',
            (price, tax, order_id)
        )

        txn_id = str(uuid4())
        cur.execute(
            'insert into transactions(id, order_id, price) '
            'values (%s, %s, %s)',
            (txn_id, order_id, total_price)
        )

        txn_token, callback_url = paytm.initiate_transaction(user_id, txn_id, total_price)

        conn.commit()

        return {
            'txn_token': txn_token,
            'callback_url': callback_url,
        }
