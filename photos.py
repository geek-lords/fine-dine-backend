from flask import Blueprint, request

from db_utils import connection

photos = Blueprint('photos', __name__)

ValidationError = 401


@photos.route('/get')
def get_photo():
    """
    Get a photo with the given id

    url - /api/v1/photos/get?id=<photo id>
    """
    photo_id = request.args.get('id')
    if not photo_id:
        return {'error': 'photo id not found'}, ValidationError

    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            'select mime_type, data from photos where id = %s',
            (photo_id,)
        )

        if cur.rowcount == 0:
            return {'error': 'No photo found'}

        row = cur.fetchone()
        mime_type = row[0]
        data = row[1]
        return data, 200, {'Content-Type': mime_type}


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}


def extension(filename):
    return filename.rsplit('.', 1)[1].lower()


def allowed_file(filename):
    return '.' in filename and \
           extension(filename) in ALLOWED_EXTENSIONS


def mime(extension):
    # other than svg, all other supported extensions have their extension
    # as images/<extension>
    if extension != 'svg':
        return 'images/' + extension

    return 'images/svg+xml'


@photos.route('/add', methods=['POST'])
def add_photo():
    """
    Sample html -
    <html>
    <body>
    <form action="http://localhost:5000/api/v1/photo/add" method="POST" enctype="multipart/form-data">
        <input type="file" name="restaurant_photo" />
        <input type="submit" value="Submit" />
    </form>
    </body>
    </html>

    Sample output -
    {
        "url" - "localhost:5000/api/v1/photo/get?id=1"
    }
    """
    file = request.files.get('restaurant_photo')
    if not file or not file.filename:
        return {'error': 'file not found'}, ValidationError

    if not allowed_file(file.filename):
        return {'error': 'file not allowed. You can only upload: png, jpg, jpeg, and gif'}

    ext = extension(file.filename)
    # jpg files are basically jpeg   files and they dont have their own
    # mime type. Other extensions' mime types are basically images/<extension>
    if ext == 'jpg':
        ext = 'jpeg'

    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            'insert into photos(mime_type, data) values (%s, %s)',
            (mime(ext), file.read())
        )

        cur.execute('select last_insert_id()')
        table_id = cur.fetchone()[0]
        conn.commit()

        return {
            'url': f'{request.host_url}api/v1/photo/get?id={table_id}',
        }
