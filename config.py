import os

from dotenv import load_dotenv

load_dotenv()

hostname = os.getenv('DB_HOSTNAME')
username = os.getenv('DB_USERNAME')
password = os.getenv('DB_PASSWORD')
database = os.getenv('DATABASE')
jwt_secret = os.getenv('JWT_SECRET')
