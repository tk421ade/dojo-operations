import re
from pathlib import Path

from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import render
from django.views.decorators.http import require_GET
from django_otp.decorators import otp_required
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken

from dojoconf.models import Dojo
from financial.models import Sale, MembershipProduct, Membership
from shodan.models import Student, Session, Attendance
from web.forms import EmailForm


BACKUP_TOKEN_COUNT = 10


def dev_error(request):
    """ Force an unhandled error """
    i = 1/0


@otp_required
@require_GET
def protected_file(request, path):
    """Serve a private file (student documents, waiver signatures) to authenticated staff only.

    Non-superuser staff can only access files for dojos they are assigned to.
    The path format starts with dojo_<id>/ so we extract and verify the dojo.
    """
    if not request.user.is_staff:
        raise PermissionDenied

    match = re.match(r'dojo_(\d+)', path)
    if not match:
        raise Http404

    dojo_id = int(match.group(1))

    if not request.user.is_superuser:
        if not Dojo.objects.filter(id=dojo_id, users=request.user).exists():
            raise PermissionDenied

    private_root = Path(settings.PRIVATE_STORAGE_ROOT).resolve()
    file_path = (private_root / path).resolve()

    if not file_path.is_relative_to(private_root) or not file_path.is_file():
        raise Http404

    return FileResponse(open(file_path, 'rb'))


@otp_required
def backup_reveal(request):
    """Reveal one-time backup codes right after TOTP enrollment.

    Generates a fresh set of static tokens if the user has none, then renders
    them with a lockout warning. Reached via SetupView.success_url. See HLD U10.12.
    """
    user = request.user
    device = StaticDevice.objects.filter(user=user).first()
    if device is None:
        device = StaticDevice.objects.create(user=user, name='backup')
        for _ in range(BACKUP_TOKEN_COUNT):
            StaticToken.objects.create(device=device, token=StaticToken.random_token())
    tokens = list(device.token_set.all().values_list('token', flat=True))
    next_url = request.session.get('next') or '/admin/'
    return render(request, 'two_factor/backup_reveal.html', {
        'tokens': tokens,
        'next_url': next_url,
    })
