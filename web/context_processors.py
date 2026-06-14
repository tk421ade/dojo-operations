from dojoconf.models import Dojo


def dojo_context(request):
    dojo_id = request.session.get('dojo_id')
    if dojo_id:
        try:
            return {'dojo': Dojo.objects.get(id=dojo_id)}
        except Dojo.DoesNotExist:
            pass
    return {'dojo': None}
