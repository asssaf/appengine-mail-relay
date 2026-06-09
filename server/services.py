import datetime
import os
import traceback
import sys

import dateutil.tz
from google.appengine.api import app_identity, mail
from google.cloud import monitoring_v3

def get_application_id():
    return app_identity.get_application_id()

def send_email(sender, recipient, body):
    email_msg = mail.EmailMessage(
        mime_message=body,
        sender=sender,
        to=recipient,
    )
    email_msg.Send()

def send_admin_email(sender, subject, body):
    email_msg = mail.AdminEmailMessage(
        subject=subject,
        body=body,
        sender=sender,
    )
    email_msg.Send()

def get_successful_sends():
    client = monitoring_v3.MetricServiceClient()
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        raise Exception("GOOGLE_CLOUD_PROJECT environment variable is not set")

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
    return None
