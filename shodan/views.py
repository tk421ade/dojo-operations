import re
from pathlib import Path

from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.views.decorators.http import require_GET

from dojoconf.models import Dojo
from financial.models import Sale, MembershipProduct, Membership
from shodan.models import Student, Session, Attendance
from web.forms import EmailForm


def dev_error(request):
    """ Force an unhandled error """
    i = 1/0


@login_required
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
