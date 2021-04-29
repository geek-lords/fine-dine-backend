import logging

from flask import Flask, url_for

from admin_endpoints import admin
from user_endpoints import user

app = Flask(__name__)
app.register_blueprint(user, url_prefix='/api/v1')
app.register_blueprint(admin, url_prefix='/api/v1/admin')
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s %(name)s %(asctime)s %(message)s')

if __name__ == '__main__':
    app.run(debug=True)
