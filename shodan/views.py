from dojoconf.models import Dojo
from financial.models import Sale, MembershipProduct, Membership
from shodan.models import Student, Session, Attendance
from web.forms import EmailForm


def dev_error(request):
    """ Force an unhandled error """
    i = 1/0
