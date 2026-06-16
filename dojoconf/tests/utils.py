from django.contrib.auth import get_user_model
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_totp.models import TOTPDevice


def print_form_errors_from_response(response):
    # Check for form validation errors
    if response.context and response.context['adminform'].errors:
        # Form validation errors exist
        print("Form validation errors:")
        for field, errors in response.context['adminform'].errors.items():
            print(f"{field}: {errors}")


def login_verified(client, username='admin', password='password'):
    """Log the test client in AND establish an OTP-verified session.

    Django's Client.login() authenticates the user but does not verify them
    (no OTP token is entered). Since the admin now requires two-factor
    verification (HLD U10), any test exercising the admin must also mark the
    session as verified by persisting a TOTP device id, exactly as
    django_otp.middleware.OTPMiddleware does for a real verified login.
    """
    client.login(username=username, password=password)
    user = get_user_model().objects.get(username=username)
    device = TOTPDevice.objects.create(user=user, name='test')
    session = client.session
    session[DEVICE_ID_SESSION_KEY] = device.persistent_id
    session.save()
