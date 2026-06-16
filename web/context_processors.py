from django.utils.timezone import now as tz_now

from dojoconf.models import Dojo


def dojo_context(request):
    context = {'dojo': None, 'current_year': tz_now().year}
    dojo_id = request.session.get('dojo_id')
    if dojo_id:
        try:
            context['dojo'] = Dojo.objects.get(id=dojo_id)
        except Dojo.DoesNotExist:
            pass
    return context
