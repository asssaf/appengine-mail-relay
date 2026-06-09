import json
import os
import sys
import time
import traceback

from nacl.encoding import HexEncoder
from nacl.signing import SigningKey, VerifyKey
from flask import abort, Flask, request

from google.appengine.api import wrap_wsgi_app
try:
    from . import services
except ImportError:
    import services

TIME_FUDGE_SECONDS = 120

app = Flask(__name__)

# Only wrap with wrap_wsgi_app if not in testing mode
if not os.environ.get('TESTING'):
    app.wsgi_app = wrap_wsgi_app(app.wsgi_app)

_verify_key_cache = None

def get_verify_key():
    global _verify_key_cache
    if _verify_key_cache:
        return _verify_key_cache

    verify_key_bytes = os.environ.get('PUBLIC_KEY')
    if verify_key_bytes:
        _verify_key_cache = VerifyKey(verify_key_bytes, encoder=HexEncoder)
        return _verify_key_cache
    return None


@app.route('/notification', methods=['POST'])
def sendNotification():
    data = request.json
    if not data or "signature" not in data:
        print("missing signature")
        abort(401)

    signature_hex = data["signature"]

    verify_key = get_verify_key()
    if not verify_key:
        print("verify key not configured")
        abort(500)

    try:
        msg = verify_key.verify(signature_hex, encoder=HexEncoder)
    except Exception as e:
        print("verification error: ", e)
        abort(401)


    try:
        decoded = json.loads(msg)
        body = decoded['body']
        timestamp = decoded['timestamp']

    except Exception as e:
        print("decoding error: ", e)
        abort(400)

    current_time = int(time.time())
    if abs(current_time-timestamp) > TIME_FUDGE_SECONDS:
        print("message expired, timestamp=%d, current=%d" % (timestamp, current_time))
        abort(400)


    sender_address='noreply@{}.appspotmail.com'.format(services.get_application_id())
    recipient_address=os.environ.get('SEND_TO')

    try:
        services.send_email(
            sender=sender_address,
            recipient=recipient_address,
            body=body
        )
        print("email sent")
        return notifySends()
    except Exception as e:
        print("error in send: ", e)
        abort(500)


@app.route('/key')
def generateKey():
    signing_key = SigningKey.generate()
    signing_key_bytes = signing_key.encode(encoder=HexEncoder)
    verify_key = signing_key.verify_key
    verify_key_bytes = verify_key.encode(encoder=HexEncoder)

    return json.dumps({
        "private_key": signing_key_bytes.decode('ascii'),
        "public_key": verify_key_bytes.decode('ascii')
    }), 200, {'Content-Type': 'application/json'}


@app.route('/health')
def health():
    return notifySends(), 200, {'Content-Type': 'application/json'}


def notifySends():
    try:
        results = services.get_successful_sends()
        if not results:
             return json.dumps({})

        sends = results.points[0].value.int64_value
        if sends in [60, 90, 120, 122]:
            sender_address='noreply@{}.appspotmail.com'.format(services.get_application_id())

            try:
                services.send_admin_email(
                    sender=sender_address,
                    subject="appengine-mail-relay admin notification",
                    body="Messages sent at %d" % sends
                )
                print("admin email sent")
                return json.dumps({})
            except Exception as e:
                print("error in admin send: ", e)
                abort(500)

        return json.dumps({})

    except Exception:
        exc_info = sys.exc_info()
        err = ''.join(traceback.format_exception(*exc_info))
        return json.dumps({
            "error": err,
        })


if __name__ == '__main__':
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    # Flask's development server will automatically serve static files in
    # the "static" directory. See:
    # http://flask.pocoo.org/docs/1.0/quickstart/#static-files. Once deployed,
    # App Engine itself will serve those files as configured in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)
