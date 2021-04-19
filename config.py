import os

from dotenv import load_dotenv

load_dotenv()

hostname = os.getenv('DB_HOSTNAME')
username = os.getenv('DB_USERNAME')
password = os.getenv('DB_PASSWORD')
database = os.getenv('DATABASE')

jwt_secret = os.getenv('JWT_SECRET')

merchant_id = os.getenv('MERCHANT_ID')
merchant_key = os.getenv('MERCHANT_KEY')

website = os.getenv('WEBSITE')
callback_url = os.getenv('CALLBACK_URL')