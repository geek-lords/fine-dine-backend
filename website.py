from flask import Blueprint, send_from_directory

website = Blueprint('website', __name__)


@website.route('/')
def home_page():
    return send_from_directory('frontend/fine-dine/public', 'webpages/homepage.html')


@website.route('/assets/<path:p>')
def get_asset(p):
    return send_from_directory('frontend/fine-dine/public/assets/', p)


@website.route('/js/<path:p>')
def get_js(p):
    return send_from_directory('frontend/fine-dine/public/js/', p)


@website.route('/<path:p>')
def get_page(p):
    return send_from_directory('frontend/fine-dine/public/webpages', p)


@website.route('/styles.css')
def get_styles():
    return send_from_directory('frontend/fine-dine/public/webpages', 'styles.css')
