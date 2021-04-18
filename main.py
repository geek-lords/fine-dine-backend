from flask import Flask, url_for

from admin_endpoints import admin
from user_endpoints import user

app = Flask(__name__)
app.register_blueprint(user, url_prefix='/api/v1')
app.register_blueprint(admin, url_prefix='/api/v1/admin')

if __name__ == '__main__':
    app.run(debug=True)
