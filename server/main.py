import datetime
import email
import json
import os
import time

from nacl.encoding import HexEncoder
from nacl.signing import SigningKey, VerifyKey, SignedMessage
from flask import abort, Flask, request

from google.appengine.api import app_identity, mail, wrap_wsgi_app

TIME_FUDGE_SECONDS = 120

app = Flask(__name__)
app.wsgi_app = wrap_wsgi_app(app.wsgi_app)

verify_key_bytes = os.environ.get('PUBLIC_KEY')
if verify_key_bytes:
    verify_key = VerifyKey(verify_key_bytes, encoder=HexEncoder)


@app.route('/notification', methods=['POST'])
def sendNotification():
    data = request.json
    signature_hex = data["signature"]
    if not signature_hex:
        print("missing signature")
        abort(401)


    try:
        msg = verify_key.verify(signature_hex, encoder=HexEncoder)
    except Exception as e:
        print("verification error: ", e)
        abort(401)


    try:
        decoded = json.loads(msg)

        subject = decoded['subject']
        body = decoded['body']
        timestamp = decoded['timestamp']

    except Exception as e:
        print("decoding error: ", e)
        abort(400)

    current_time = int(time.time())
    if abs(current_time-timestamp) > TIME_FUDGE_SECONDS:
        print("message expired, timestamp=%d, current=%d" % (timestamp, current_time))
        abort(400)



    mime_message = email.message_from_string(body)

    sender_address='noreply@{}.appspotmail.com'.format(app_identity.get_application_id())
    recipient_address=os.environ.get('SEND_TO')

    email_msg = mail.EmailMessage(
        mime_message=body,
        sender=sender_address,
        to=recipient_address,
    )
    email_msg.Send()


    return json.dumps({})


@app.route('/key')
def generateKey():
    signing_key = SigningKey.generate()
    signing_key_bytes = signing_key.encode(encoder=HexEncoder)
    verify_key = signing_key.verify_key
    verify_key_bytes = verify_key.encode(encoder=HexEncoder)

    return json.dumps({
        "private_key": signing_key_bytes.decode('ascii'),
        "public_key": verify_key_bytes.decode('ascii')
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
