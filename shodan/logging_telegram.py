import logging
import asyncio
from django.utils.module_loading import import_string
from django.conf import settings
from copy import copy
from telegram import Bot
from telegram.error import NetworkError

from shodan.settings import TELEGRAM_CHAT_TOKEN, TELEGRAM_CHAT_ID


class TelegramHandler(logging.Handler):
    """An exception log handler that emails log entries to site admins.

    If the request is passed as the first argument to the log record,
    request data will be provided in the email report.
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

        # Since we add a nicely formatted traceback on our own, create a copy
        # of the log record without the exception data.
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

        asyncio.run(self.send_message(subject, message))


    async def send_message(self, subject, message):


        full_message = f"{subject}\n\n{message}"
        logging.error("Error reported to telegram: %s", full_message)

        try:
            bot = Bot(token=TELEGRAM_CHAT_TOKEN)
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=full_message[:4096])
        except NetworkError as e:
            logging.error(f"Unable to send telegram ERROR report: Network error: {e}")
        except Exception as e:
            logging.error(f"Unable to send telegram ERROR report: {e}", e)

    def format_subject(self, subject):
        """
        Escape CR and LF characters.
        """
        return subject.replace("\n", "\\n").replace("\r", "\\r")