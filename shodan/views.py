import urllib.parse
from datetime import datetime, date, timedelta
from enum import member
from typing import Any

import pytz
from django.contrib import messages
from django.contrib.sessions.backends.base import SessionBase
from django.contrib.sessions.backends.cache import SessionStore
from django.shortcuts import render, redirect

from dojoconf.models import Dojo
from financial.models import Sale, MembershipProduct, Membership
from shodan.models import Student, Session, Attendance
from web.forms import EmailForm


def dev_error(request):
    """ Force an unhandled error """
    i = 1/0
