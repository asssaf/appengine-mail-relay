import datetime
import json
import os
import sys
import time
import traceback

import dateutil.tz
from nacl.encoding import HexEncoder
from nacl.signing import SigningKey, VerifyKey
from flask import abort, Flask, request

from google.appengine.api import app_identity, mail, wrap_wsgi_app
from google.cloud import monitoring_v3

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

        #subject = decoded['subject']
        body = decoded['body']
        timestamp = decoded['timestamp']

    except Exception as e:
        print("decoding error: ", e)
        abort(400)

    current_time = int(time.time())
    if abs(current_time-timestamp) > TIME_FUDGE_SECONDS:
        print("message expired, timestamp=%d, current=%d" % (timestamp, current_time))
        abort(400)



    #mime_message = email.message_from_string(body)

    sender_address='noreply@{}.appspotmail.com'.format(app_identity.get_application_id())
    recipient_address=os.environ.get('SEND_TO')

    email_msg = mail.EmailMessage(
        mime_message=body,
        sender=sender_address,
        to=recipient_address,
    )

    try:
        email_msg.Send()
        print("email sent")
        notifySends()
    except Exception as e:
        print("error in send: ", e)
        abort(500)

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


@app.route('/health')
def health():
    return notifySends()


def notifySends():
    try:
        results = getSuccessfulSends()

        sends = results.points[0].value.int64_value
        if sends in [60, 90, 120, 122]:
            sender_address='noreply@{}.appspotmail.com'.format(app_identity.get_application_id())
            email_msg = mail.AdminEmailMessage(
                subject="appengine-mail-relay admin notification",
                body="Messages sent at %d" % sends,
                sender=sender_address,
            )

            try:
                email_msg.Send()
                print("admin email sent")
                return json.dumps({})
            except Exception as e:
                print("error in admin send: ", e)
                abort(500)

    except Exception:
        exc_info = sys.exc_info()
        err = ''.join(traceback.format_exception(*exc_info))
        return json.dumps({
            "error": err,
        })


def getSuccessfulSends():
    client = monitoring_v3.MetricServiceClient()
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        abort(500)

    project_name = f"projects/{project_id}"

    tz = dateutil.tz.gettz('US/Pacific')
    now = datetime.datetime.now(tz)
    now_seconds = int(now.timestamp())
    now_nanos = 0
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    midnight_seconds = int(midnight.timestamp())
    midnight_nanos = 0
    interval = monitoring_v3.TimeInterval(
        {
            "end_time": {"seconds": now_seconds, "nanos": now_nanos},
            "start_time": {"seconds": midnight_seconds, "nanos": midnight_nanos},
        }
    )
    print("interval: ", interval)

    # sum over the entire interval
    aggregation_seconds = now_seconds - midnight_seconds

    aggregation = monitoring_v3.Aggregation(
        {
            "alignment_period": {"seconds": aggregation_seconds},
            "per_series_aligner": monitoring_v3.Aggregation.Aligner.ALIGN_SUM,
            "group_by_fields": ["resource.zone"],
        }
    )

    results = client.list_time_series(
        request={
           "name": project_name,
           "filter": 'metric.type = "logging.googleapis.com/user/mail.send"',
           "interval": interval,
           "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
           "aggregation": aggregation,
        }
    )

    for result in results:
        return result


if __name__ == '__main__':
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    # Flask's development server will automatically serve static files in
    # the "static" directory. See:
    # http://flask.pocoo.org/docs/1.0/quickstart/#static-files. Once deployed,
    # App Engine itself will serve those files as configured in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)
