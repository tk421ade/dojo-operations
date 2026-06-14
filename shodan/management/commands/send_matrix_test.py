from django.conf import settings
from django.core.management.base import BaseCommand

from shodan.logging_matrix import send_matrix_message


class Command(BaseCommand):
    help = "Send a test message to the configured Matrix room to verify connectivity."

    def add_arguments(self, parser):
        parser.add_argument(
            "--message",
            default="Test message from Shodan management command.",
            help="Custom message text to send (default: a standard test message).",
        )

    def handle(self, *args, **options):
        homeserver = getattr(settings, "MATRIX_HOMESERVER_URL", None)
        access_token = getattr(settings, "MATRIX_ACCESS_TOKEN", None)
        room_id = getattr(settings, "MATRIX_ROOM_ID", None)

        if not all([homeserver, access_token, room_id]):
            self.stdout.write(self.style.ERROR(
                "Matrix is not configured. Set these environment variables:\n"
                "  MATRIX_HOMESERVER_URL\n"
                "  MATRIX_ACCESS_TOKEN\n"
                "  MATRIX_ROOM_ID"
            ))
            return

        self.stdout.write(f"Homeserver : {homeserver}")
        self.stdout.write(f"Room ID    : {room_id}")
        self.stdout.write("Sending test message ...")

        success = send_matrix_message(options["message"])

        if success:
            self.stdout.write(self.style.SUCCESS(
                "Message delivered. Check the Matrix room to confirm receipt."
            ))
        else:
            self.stdout.write(self.style.ERROR(
                "Message was NOT delivered. Check the logs above for details.\n"
                "Verify that the Matrix homeserver is running and the access token is valid."
            ))
