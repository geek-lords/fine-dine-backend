from uuid import uuid4
import bcrypt
import jwt
import pymysql
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from email_validator import EmailNotValidError, validate_email
from flask import Blueprint, request
from jwt import InvalidSignatureError
from pytz import timezone

import paytm
from config import jwt_secret, merchant_id
from db_utils import connection

MinPasswordLength = 5

user = Blueprint('user', __name__)

# scheduler = BackgroundScheduler()
#
#
# def keep_server_alive():
#     requests.get(
#         'https://fine-dine-backend.herokuapp.com/api/v1/menu?restaurant_id=6902d892-4d75-44fe-85bd-b92a60260f70'
#     )
#     print('request sent')
#
#
# scheduler.add_job(
#     keep_server_alive,
#     'interval',
#     minutes=25,
# )
#
# scheduler.start()

# HTTP error code for validation error
ValidationError = 200

MaxPasswordLength = 70


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def password_valid(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))


@user.route('/dummy')
def dummy():
    return ''


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
            print('No json data found')
            return {'error': 'No json data found'}, ValidationError

        name = str(request.json['name']).strip()

        if len(name) == 0:
            print('name invalid or empty')
            return {'error': 'name invalid or empty'}, ValidationError

        password = str(request.json['password']).strip()

        if len(password) < MinPasswordLength or len(password) > MaxPasswordLength:
            print('invalid password')
            return (
                {
                    'error': f'password should be between {MinPasswordLength} '
                             f'and {MaxPasswordLength} characters'
                },
                ValidationError
            )

        email = str(request.json['email']).strip()
        try:
            # validating email and assigning the valid email back to email
            email = validate_email(email).email
        except EmailNotValidError:
            print('email not valid')
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
        print('Invalid input. One or more parameters absent')
        return {'error': 'Invalid input. One or more parameters absent'}, ValidationError
    except pymysql.err.IntegrityError:
        print('User already exists')
        return {'error': 'User already exists'}, ValidationError


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
            print('No json data found')
            return {'error': 'No json data found'}, ValidationError

        email = str(request.json['email'])
        password = str(request.json['password'])

        if len(password) < MinPasswordLength or len(password) > MaxPasswordLength:
            print('Invalid password')
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
            print('email is not valid')
            return {'error': 'email is not valid'}, ValidationError

        with connection() as conn, conn.cursor() as cur:
            cur.execute(
                'select id, password_hash from users where email = %s',
                # execute needs a tuple of parameters. comma converts
                # (email) into a tuple containing one element - email
                (email,),
            )

            if cur.rowcount == 0:
                print('Invalid email or password')
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
        print('Invalid input. One or more parameters absent')
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
    except jwt.exceptions.DecodeError:
        return None


@user.route('/menu')
def get_menu():
    """
        url - /api/v1/menu?restaurant_id=jhcvxjdsvydsgvfshgho
        Sample output -
        {
            "restaurant": "name of restaurant"
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
        print('restaurant id missing')
        return {'error': 'Invalid input. One or more parameters absent'}, ValidationError

    with connection() as conn, conn.cursor() as cur:
        cur.execute('select name from restaurant where id = %s', (restaurant_id,))

        if cur.rowcount == 0:
            print('restaurant id does not exist')
            return {'error': 'Restaurant does not exist'}, ValidationError

        restaurant = cur.fetchone()[0]

        cur.execute(
            'select id, name, description, photo_url, price '
            'from menu '
            'where restaurant_id = %s and active_menu = 0',
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

        return {'menu': menu, 'restaurant': restaurant}


@user.route("/order", methods=["POST"])
def create_order():
    """
    Create an order.
    url - /api/v1/order?restaurant_id=<restaurant id>&table=<table>
    Headers - X-Auth-Token: <jwt>
    Sample error -
    {
        "error": "reason for error"
    }
    Sample output -
    {
        "order_id": "38trfghere yfrguoi rgrgg",
        "tax_percent": 5.5
    }
    """
    try:
        user_id = _decoded_user_id(request)
        if not user_id:
            print('Authentication failure')
            return {'error': 'Authentication failure'}, ValidationError

        table = request.args.get('table')
        if not table:
            print('Table absent')
            return {'error': 'table parameter not found in request'}, ValidationError

        restaurant_id = request.args.get('restaurant_id')
        if not restaurant_id:
            print('Restaurant id not found')
            return {'error': 'restaurant id not found'}, ValidationError

        with connection() as conn, conn.cursor() as cur:
            cur.execute(
                'select tax_percent from restaurant where id = %s',
                (restaurant_id,)
            )

            if cur.rowcount == 0:
                print('Restaurant id does not exist')
                return {'error': 'Restaurant id does not exist'}, ValidationError

            tax_percent = float(cur.fetchone()[0])

            cur.execute(
                'select name from tables '
                'where restaurant_id = %s and id = %s',
                (restaurant_id, table)
            )

            if cur.rowcount == 0:
                print('Table not found')
                return {'error': 'Table not found'}, ValidationError

            order_id = str(uuid4())

            cur.execute(
                "insert into orders(id, user_id, table_id, restaurant_id, payment_status) "
                "values(%s, %s, %s, %s, %s)",
                (order_id, user_id, table, restaurant_id, paytm.PaymentStatus.NOT_PAID.value),
            )

            conn.commit()
        return {'order_id': order_id, 'tax_percent': tax_percent}
    except KeyError:
        print('Invalid input. One or more parameters absent')
        return {'error': 'Invalid input. One or more parameters absent'}, ValidationError


@user.route('/checkout', methods=['POST'])
def checkout():
    order_id = request.args.get('order_id')
    if not order_id:
        print('order id not found')
        return {'error': 'Order id not found'}, ValidationError

    user_id = _decoded_user_id(request)
    if not user_id:
        print('Authentication failure')
        return {'error': 'Authentication failure'}, ValidationError

    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            'select user_id, payment_status, restaurant_id from orders '
            'where id = %s',
            (order_id,)
        )

        if cur.rowcount == 0:
            print('Order id does not exist')
            return {'error': 'Invalid input. Order id does not exist'}, ValidationError

        row = cur.fetchone()
        user_id_who_created_the_order = row[0]
        payment_status = row[1]
        restaurant_id = row[2]

        if user_id != user_id_who_created_the_order:
            print('user id not the same as the person as user id who created the order')
            return {'error': 'Authentication failure'}, ValidationError

        if payment_status == paytm.PaymentStatus.SUCCESSFUL.value:
            print('Order has already been paid for')
            return {'error': 'Order has already been paid'}, ValidationError

        cur.execute(
            'select sum(price) from order_items where order_id = %s',
            (order_id,)
        )

        price = cur.fetchone()[0]
        # sum should return 0 for empty list. But it is somehow returning None
        if price == 0 or price is None:
            print('no order items found')
            return {'error': 'Please book something before checking out'}, ValidationError

        cur.execute(
            'select tax_percent from restaurant where id = %s',
            (restaurant_id,)
        )

        tax_percent = cur.fetchone()[0]
        tax = price * tax_percent / 100
        total_price = price + tax

        cur.execute(
            'update orders set tax = %s where id = %s',
            (tax, order_id)
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
    url - /api/v1/update_payment_status?txn_id=<txn_id>?status=<int>
    Headers - X-Auth-Token: <jwt>

    status can be one of payment status described below

    Sample output -
    {
        "payment_status": <payment_status>
    }
    Where payment status is one of -
    Value | Meaning
    0     | SUCCESSFUL
    1     | PENDING
    2     | INVALID
    3     | FAILED
    If there is a successful transaction against the order for which
    this transaction was initiated, then it returns -
    {
        "error": "This order has already been paid for"
    }
    :return:
    """
    user_id = _decoded_user_id(request)
    if not user_id:
        print('Authentication failed')
        return {'error': 'Authentication failed'}, ValidationError

    txn_id = request.args.get('txn_id')
    if not txn_id:
        print('Transaction id not found')
        return {'error': 'Transaction id not found'}, ValidationError

    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            'select order_id, payment_status from transactions '
            'where id = %s',
            (txn_id,)
        )

        if cur.rowcount == 0:
            print('Transaction id does not exist')
            return {'error': 'Transaction id does not exist'}, ValidationError

        row = cur.fetchone()
        order_id = row[0]
        payment_status = row[1]

        cur.execute('select user_id from orders where id = %s', (order_id,))
        if user_id != cur.fetchone()[0]:
            print('user id not same as person who created the order')
            return {'error': 'Authentication failed'}, ValidationError

        # if the payment is not done or pending, only then we need to update the status
        # otherwise, we already have the latest status
        if payment_status != paytm.PaymentStatus.NOT_PAID.value \
                and payment_status != paytm.PaymentStatus.PENDING.value:
            return {'success': payment_status == paytm.PaymentStatus.SUCCESSFUL.value}

        status = request.args.get('status')
        # cannot use "if not status" here because status of 0 will go to false
        if status is not None:
            updated_payment_status = paytm.PaymentStatus.parse(status)
        else:
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
    """
    Add items to order.
    url - /api/v1/order_items?order_id=jhcvxjdsvydsgvfshgho
    Headers - X-Auth-Token: <jwt>
    sample input -
    {
        "order_list": [
            {
                "menu_id": 1,
                "quantity": 2
            },
            {
                "menu_id": 2,
                "quantity": 3
            }
        ]
    }
    sample output -
    {
        "success": true
    }
    sample error -
    {
        "error": "reason for error"
    }
    """
    try:
        if not request.json:
            print('no json found')
            return {"error": "Invalid Request/ No Json Data Found."}, ValidationError

        order_id = request.args.get("order_id")

        if not order_id:
            print('no order id found')
            return {'error': 'Invalid request'}, ValidationError

        user_id = _decoded_user_id(request)
        if not user_id:
            print('Authentication error')
            return {'error': 'Authentication error'}, ValidationError

        all_orders = list(map(lambda json: Order(order_id, int(json["menu_id"]), json["quantity"]),
                              request.json['order_list']))

        if len(all_orders) == 0:
            print('no orders found')
            return {'error': 'order items cannot be empty'}, ValidationError

        for order in all_orders:
            if not order.is_valid():
                print('invalid input. menu id: ' + order.menu_id + '\t quantity: ' + order.quantity)
                return {"error": "Invalid input"}, ValidationError

        menu_ids = tuple(map(lambda order: order.menu_id, all_orders))

        if len(set(menu_ids)) != len(menu_ids):
            print('menu id repeated: %s' % list(menu_ids))
            return {'error': 'Menu id cannot be repeated'}, ValidationError

        with connection() as conn, conn.cursor() as cur:
            cur.execute(
                'select user_id from orders where id = %s',
                (order_id,)
            )

            if cur.rowcount == 0:
                print('No such order found')
                return {'error': 'No such order found'}, ValidationError

            if cur.fetchone()[0] != user_id:
                print('Authorization error')
                return {'error': 'Authorization error'}, ValidationError

            cur.execute('select id, price, restaurant_id, active_menu from menu where id in %s', (menu_ids,))
            rows = cur.fetchall()
            restaurant_ids = list(map(lambda row: row[2], rows))
            active_menus = list(map(lambda row: row[3], rows))

            if 1 in active_menus:
                return {"error": "Can't order Disabled Items."}, ValidationError

            if len(restaurant_ids) == 0:
                print('Menu id does not exist')
                return {'error': 'Menu id does not exist'}, ValidationError

            if len(set(restaurant_ids)) != 1:
                print('Cannot order from multiple restaurants')
                return {'error': 'Cannot order from multiple restaurants'}, ValidationError

            if len(restaurant_ids) != len(menu_ids):
                print('One or more menu ides does not exist')
                return {'error': 'One or more menu ids does not exist'}, ValidationError

            prices = {}
            for id, price, _, x in rows:
                prices[id] = float(price)

            for order in all_orders:
                order.price = prices[order.menu_id] * order.quantity
                print('menu id: ' + str(order.menu_id))
                print('price: ' + str(prices[order.menu_id]))

            # execute many raises type error for some reason
            for order in all_orders:
                cur.execute(
                    "insert into order_items(order_id, menu_id, quantity, price) values "
                    "(%s,%s,%s,%s) on duplicate key "
                    "update quantity = quantity + %s, price = price + %s ",
                    (order.order_id, order.menu_id, order.quantity,
                     order.price, order.quantity, order.price)
                )
                cur.execute("insert into new_orders(id, order_id, menu_id, quantity) values(%s,%s,%s,%s)",
                            (uuid4(), order.order_id, order.menu_id, order.quantity))
            price_excluding_tax = sum(map(lambda o: o.price, all_orders))

            cur.execute("update orders set price_excluding_tax = price_excluding_tax + %s where id = %s",
                        (price_excluding_tax, order_id))

            conn.commit()

        return {"success": True}
    except (KeyError, TypeError) as e:
        print('Invalid input: ' + e)
        return {'error': 'Invalid input'}, ValidationError


@user.route("/order_history", methods=['POST'])
def get_order_history():
    """
        This route shows order history for a user.
        Sample Input :  send JWT as token - X-Auth-Token
        Sample Output(List of all orders) :

        This route shows orders made by a particular user.

        Sample Input: send a JSON, POST request. add a X-Auth-Token in Header of request and send JWT Token
                      as value of X-Auth-Token.
        Sample Output:
        {
            "history":
                [
                    {
                      "id": "3a9d8156-6c65-4a61-9f19-df612251223b",
                      "name": "Joshi Bhojangrih",
                      "photo_url": "goal.jpeg",
                      "price": "650.00",
                      "tax_percent": "18.00",
                      "time_and_date": "2021-05-08 03:44"
                    },
                    {
                      "id": "3a9d8156-6c65-4a61-9f19-df612254223b",
                      "name": "Joshi Bhojangrih",
                      "photo_url": "goal.jpeg",
                      "price": "350.00",
                      "tax_percent": "18.00",
                      "time_and_date": "2021-05-08 03:44"
                    }
                ]
        }
        Here, id shows order_id.

        else, An Error is returned.
    """
    try:
        user_id = _decoded_user_id(request)
        if user_id is None:
            print('Username not found')
            return {"error": "Username can't be None."}, ValidationError
        with connection() as conn, conn.cursor() as cur:
            cur.execute(
                "Select orders.id, restaurant.name, orders.price_excluding_tax+orders.tax, orders.time_and_date,"
                "restaurant.tax_percent,restaurant.photo_url "
                "from orders "
                "join restaurant on orders.restaurant_id = restaurant.id "
                "where orders.user_id= %s "
                "order by orders.time_and_date desc",
                (user_id,)
            )

            order_history = cur.fetchall()

            result = []

            for order_id, name, price, time_and_date, tax, photo_url in order_history:
                # IST is an abbreviation. So I have used capital letters
                # which gives a warning. The next comment disables the warning
                # noinspection PyPep8Naming
                time_and_date_in_IST = time_and_date.astimezone(timezone('Asia/Kolkata'))
                time_and_date = time_and_date_in_IST.strftime("%I:%M %p %d/%m/%Y")

                result.append({
                    'id': order_id,
                    'name': name,
                    'photo_url': photo_url,
                    'price': str(price),
                    'tax_percent': str(tax),
                    'time_and_date': time_and_date
                })

            return {"history": result}

    except KeyError:
        print('Invalid input')
        return {"error": "User Token expected."}, ValidationError


@user.route("/order_history/<order_id>", methods=['POST'])
def individual_order_history(order_id):
    """
        This route gives extra Information about a particular order by a user. i.e. Bill

        Sample Input: A JSON, POST request. With Header X-Auth-Token with value as JWT Token should be
                      sent at URL/order_history/<required order id>

        Sample Output:
        {
            "bill":
                [
                    {
                      "name": "Wada Sambar",
                      "price": "90.00",
                      "quantity": "10"
                    },
                    {
                      "name": "Tea",
                      "price": "15.00",
                      "quantity": "3"
                    }
                ]
        }
    """
    try:
        user_id = _decoded_user_id(request)
        if not user_id:
            print('user id not found')
            return {"error": "User ID can't be None."}, ValidationError

        #     Authenticating the Order and User Relation
        with connection() as conn, conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute("Select user_id from orders where id = %s", order_id)
            order_user_id = cur.fetchone()['user_id']

            if str(order_user_id) != user_id:
                print('order user id not same as user id')
                return {"error": "Invalid Requesting User."}, ValidationError

            # Get Overall Information
            cur.execute(
                "select menu.name, menu.price, order_items.quantity from menu "
                "join order_items on menu.id = order_items.menu_id "
                "where order_items.order_id = %s ",
                order_id,
            )

            if cur.rowcount < 1:
                print('order items not found')
                return {"error": "Invalid Order Request"}, ValidationError

            bill = cur.fetchall()
            for bills in bill:
                bills['price'] = str(bills['price'])
                bills['quantity'] = str(bills['quantity'])

            return {"bill": bill}
    except KeyError:
        print('invalid input')
        return {"error": "Invalid Parameters found. "}, ValidationError


@user.route('/user', methods=['GET'])
def get_user():
    """
    Headers - X-Auth-Token: <jwt>

    No other input required

    Sample output -
    {
        "email": "def@abc.com",
        "name": "def"
    }
    """
    user_id = _decoded_user_id(request)
    if not user_id:
        print('Authentication error')
        return {'error': 'Authentication error'}, ValidationError

    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            'select name, email from users where id = %s',
            (user_id,)
        )

        row = cur.fetchone()
        return {
            'name': row[0],
            'email': row[1],
        }


@user.route('/user', methods=['PUT'])
def update_user():
    """
    Headers - X-Auth-Token: <jwt>

    Sample input -
    {
        "name": "<new name>"
        "email": "new email"
    }

    Sample error -
    {
        "error": "<reason for error>"
    }

    Sample output -
    {
        "email": "def@abc.com",
        "name": "def"
    }
    """
    user_id = _decoded_user_id(request)
    if not user_id:
        print('Authentication error')
        return {'error': 'Authentication error'}, ValidationError

    if not request.json:
        print('no json data found')
        return {'error': 'Invalid input'}, ValidationError

    name = str(request.json.get('name', '')).strip()
    email = str(request.json.get('email', '')).strip()

    if not email or not name:
        print('Email or name not found')
        return {'error': 'Invalid input'}, ValidationError

    try:
        # validating email and assigning the valid email back to email
        email = validate_email(email).email
    except EmailNotValidError:
        print('invalid email')
        return {'error': 'email is not valid'}, ValidationError

    with connection() as conn, conn.cursor() as cur:
        cur.execute('update users set name = %s, email = %s where id = %s', (name, email, user_id))
        conn.commit()

    return {}
