import json
import logging
import time
import urllib.request
import urllib.error
from copy import copy

from django.conf import settings
from django.utils.module_loading import import_string


def send_matrix_message(text):
    """Send a text message to the configured Matrix room.

    Returns True on success, False if Matrix is not configured or the request failed.
    Uses the Matrix Client-Server API v3 (same protocol as the production monit-matrix script).
    """
    homeserver = getattr(settings, 'MATRIX_HOMESERVER_URL', None)
    access_token = getattr(settings, 'MATRIX_ACCESS_TOKEN', None)
    room_id = getattr(settings, 'MATRIX_ROOM_ID', None)

    if not all([homeserver, access_token, room_id]):
        return False

    txn_id = f"shodan-{int(time.time() * 1000)}"
    url = (
        f"{homeserver.rstrip('/')}"
        f"/_matrix/client/v3/rooms/{room_id}/send/m.room.message/{txn_id}"
    )

    payload = json.dumps({
        "msgtype": "m.text",
        "body": text,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="PUT")
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError) as e:
        logging.error("Unable to send Matrix message: %s", e)
        return False
    except Exception as e:
        logging.error("Unable to send Matrix message: %s", e)
        return False


class MatrixHandler(logging.Handler):
    """Exception log handler that sends error reports to a Matrix room.

    Mirrors Django's AdminEmailHandler structure but delivers via the
    Matrix Client-Server API v3 instead of email.
    """

    def __init__(self):
        super().__init__()
        self.reporter_class = import_string(settings.DEFAULT_EXCEPTION_REPORTER)

    def emit(self, record):
        try:
            request = record.request
            subject = "%s (%s IP): %s" % (
                record.levelname,
                (
                    "internal"
                    if request.META.get("REMOTE_ADDR") in settings.INTERNAL_IPS
                    else "EXTERNAL"
                ),
                record.getMessage(),
            )
        except Exception:
            subject = "%s: %s" % (record.levelname, record.getMessage())
            request = None

        subject = self.format_subject(subject)

        no_exc_record = copy(record)
        no_exc_record.exc_info = None
        no_exc_record.exc_text = None

        if record.exc_info:
            exc_info = record.exc_info
        else:
            exc_info = (None, record.getMessage(), None)

        reporter = self.reporter_class(request, is_email=True, *exc_info)
        message = "%s\n\n%s" % (
            self.format(no_exc_record),
            reporter.get_traceback_text(),
        )

        full_message = f"{subject}\n\n{message}"
        logging.error("Error reported to matrix: %s", full_message)

        send_matrix_message(full_message)

    def format_subject(self, subject):
        """
        Escape CR and LF characters.
        """
        return subject.replace("\n", "\\n").replace("\r", "\\r")
