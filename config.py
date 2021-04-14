import os

from dotenv import load_dotenv

load_dotenv()

connection_url = os.getenv('CONNECTION_URL')
jwt_secret = os.getenv('JWT_SECRET')
