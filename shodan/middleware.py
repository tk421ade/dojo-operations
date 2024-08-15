import pytz
from django.contrib.auth.models import User
from django.contrib.sessions.backends.cache import SessionStore
from django.utils import timezone

from dojoconf.models import Dojo


class TimezoneMiddleware:
    """
    Activate the correct user timezone
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user: User = request.user
        session: SessionStore = request.session
        if not session.has_key('user_timezone'):
            dojos = Dojo.objects.filter(users__username=user.username)
            if len(dojos) > 0:
                dojo = dojos[0]
                session['user_timezone'] = dojo.timezone.key
                timezone.activate(dojo.timezone)

        return self.get_response(request)

class DojoPermissionsMiddleware:
    """
    Filter the dojos that the user has permission to
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user: User = request.user
        session: SessionStore = request.session
        if not session.has_key('user_dojos'):
            dojos = Dojo.objects.filter(users__username=user.username)
            dojos_ids = []
            for dojo in dojos:
                dojos_ids.append(dojo.id)
            session['user_dojos'] = dojos_ids

        return self.get_response(request)
