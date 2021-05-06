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
from config import jwt_secret, merchant_id
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
    """
        url - /api/v1/menu?restaurant_id=jhcvxjdsvydsgvfshgho

        Sample output -
        {
            "menu": [
                {
                    "id": 1,
                    "name": "name of menu item 1",
                    "description": "description of menu item 1",
                    "photo_url": "http://google.com"
                    "price": 50.5
                },
                {
                    "id": 2,
                    "name": "name of menu item 2",
                    "description": "description of menu item 2",
                    "photo_url": "http://google.com"
                    "price": 50.5
                },
            ],
        }

        Sample error -
        {
            "error": "reason for error"
        }
        :return:
        """
    restaurant_id = request.args.get('restaurant_id')
    if not restaurant_id:
        return {'error': 'Invalid input. One or more parameters absent'}

    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            'select id, name, description, photo_url, price '
            'from menu '
            'where restaurant_id = %s',
            (restaurant_id,)
        )

        menu = []

        for id, name, description, photo_url, price in cur.fetchall():
            menu.append(
                {
                    'id': id,
                    'name': name,
                    'description': description,
                    'photo_url': photo_url,
                    # price is stored as decimal during conversion
                    # which cannot be converted to json by default.
                    # So I am converting it to float which can be
                    # used in json
                    'price': float(price),
                }
            )

        return {'menu': menu}


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
                'select tax_percent from restaurant where id = %s',
                (restaurant_id,)
            )

            if cur.rowcount == 0:
                return {'error': 'Restaurant id does not exist'}, ValidationError

            tax_percent = float(cur.fetchone()[0])

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
                (order_id, user_id, table_name, restaurant_id, paytm.PaymentStatus.NOT_PAID.value),
            )

            conn.commit()
        return {'order_id': order_id, 'tax_percent': tax_percent}
    except KeyError:
        return {'error': 'Invalid input. One or more parameters absent'}, ValidationError


@user.route('/checkout', methods=['POST'])
def checkout():
    order_id = request.args.get('order_id')
    if not order_id:
        return {'error': 'Order id not found'}, ValidationError

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
            'insert into transactions(id, order_id, price, payment_status) '
            'values (%s, %s, %s, %s)',
            (txn_id, order_id, total_price, paytm.PaymentStatus.NOT_PAID.value)
        )

        txn_token, callback_url = paytm.initiate_transaction(user_id, txn_id, total_price)

        conn.commit()

        return {
            'txn_id': txn_id,
            'm_id': merchant_id,
            'token': txn_token,
            'callback_url': callback_url,
            'amount': str(total_price)
        }


@user.route('/update_payment_status', methods=['POST'])
def update_payment_status():
    """
    Updates transaction status for the given transaction id

    If the payment status is set to successful in the database, returns -
    {
        "success": true
    }

    If the payment status is set to failed or invalid in database, returns -
    {
        "success": false
    }

    If there is a successful transaction against the order for which
    this transaction was initiated, then it returns -
    {
        "error": "This order has already been paid for"
    }

    If none of the above conditions are true, fetches the updated
    payment status from paytm and returns -
    {
        "payment_status": <payment_status>
    }

    Payment status -

    Value | Meaning
    0     | SUCCESSFUL
    1     | PENDING
    2     | INVALID
    3     | FAILED

    :return:
    """
    user_id = _decoded_user_id(request)
    if not user_id:
        return {'error': 'Authentication failed'}, ValidationError

    txn_id = request.args.get('txn_id')
    if not txn_id:
        return {'error': 'Transaction id not found'}, ValidationError

    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            'select order_id, payment_status from transactions '
            'where id = %s',
            (txn_id,)
        )

        if cur.rowcount == 0:
            return {'error': 'Transaction id does not exist'}, ValidationError

        row = cur.fetchone()
        order_id = row[0]
        payment_status = row[1]

        cur.execute('select user_id from orders where id = %s', (order_id,))
        if user_id != cur.fetchone()[0]:
            return {'error': 'Authentication failed'}, ValidationError

        # if the payment is not done or pending, only then we need to update the status
        # otherwise, we already have the latest status
        if payment_status != paytm.PaymentStatus.NOT_PAID.value \
                and payment_status != paytm.PaymentStatus.PENDING.value:
            return {'success': payment_status == paytm.PaymentStatus.SUCCESSFUL.value}

        # check if there are successful transactions against this order id
        cur.execute(
            'select id from transactions '
            'where order_id = %s '
            'and id != %s '
            'and payment_status = %s',
            (order_id, txn_id, paytm.PaymentStatus.SUCCESSFUL.value)
        )

        if cur.rowcount != 0:
            return {'error': 'This order has already been paid for. '
                             'Please cancel the transaction on your end'}, ValidationError

        updated_payment_status = paytm.payment_status(txn_id)

        cur.execute(
            'update transactions set payment_status = %s where id = %s',
            (updated_payment_status.value, txn_id)
        )

        cur.execute(
            'update orders set payment_status = %s where id = %s',
            (updated_payment_status.value, order_id)
        )

        conn.commit()

        return {
            'payment_status': updated_payment_status.value
        }


class Order:
    def __init__(self, order_id, menu_id, quantity, price=0):
        self.order_id = order_id
        self.menu_id = menu_id
        self.quantity = int(quantity)
        self.price = float(price)

    def is_valid(self):
        return self.menu_id is not None \
               and self.quantity is not None \
               and (0 < self.quantity < 16)


@user.route("/order_items", methods=['POST'])
def order_items():
    try:
        if not request.json:
            return {"error": "Invalid Request/ No Json Data Found."}, ValidationError

        order_id = request.args.get("order_id")

        if not order_id:
            return {'error': 'Invalid request'}, ValidationError

        user_id = _decoded_user_id(request)
        if not user_id:
            return {'error': 'Authentication error'}, ValidationError

        all_orders = list(map(lambda json: Order(order_id, json["menu_id"], json["quantity"]),
                              request.json['order_list']))

        if len(all_orders) == 0:
            return {'error': 'order items cannot be empty'}, ValidationError

        for order in all_orders:
            if not order.is_valid():
                return {"error": "Invalid input"}, ValidationError

        menu_ids = tuple(map(lambda order: order.menu_id, all_orders))

        if len(set(menu_ids)) != len(menu_ids):
            return {'error': 'Menu id cannot be repeated'}, ValidationError

        with connection() as conn, conn.cursor() as cur:
            cur.execute(
                'select user_id from orders where id = %s',
                (order_id,)
            )

            if cur.rowcount == 0:
                return {'error': 'No such order found'}, ValidationError

            if cur.fetchone()[0] != user_id:
                return {'error': 'Authorization error'}, ValidationError

            cur.execute('select id, price, restaurant_id from menu where id in %s', (menu_ids,))
            rows = cur.fetchall()
            restaurant_ids = list(map(lambda row: row[2], rows))

            if len(restaurant_ids) == 0:
                return {'error': 'Menu id does not exist'}, ValidationError

            if len(set(restaurant_ids)) != 1:
                return {'error': 'Cannot order from multiple restaurants'}, ValidationError

            if len(restaurant_ids) != len(menu_ids):
                return {'error': 'One or more menu ids does not exist'}, ValidationError

            prices = {}
            for id, price, _ in rows:
                prices[id] = float(price)

            for order in all_orders:
                order.price = prices[id] * order.quantity

            # execute many raises type error for some reason
            for order in all_orders:
                cur.execute(
                    "insert into order_items(order_id, menu_id, quantity, price) values "
                    "(%s,%s,%s,%s) on duplicate key "
                    "update quantity = quantity + %s, price = price + %s ",
                    (order.order_id, order.menu_id, order.quantity,
                     order.price, order.quantity, order.price)
                )

            conn.commit()

        return {"success": True}
    except (KeyError, TypeError):
        return {'error': 'Invalid input'}, ValidationError
