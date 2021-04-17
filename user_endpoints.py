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

    sample output -
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
