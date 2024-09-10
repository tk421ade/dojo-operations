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


def _is_hostname_configured(request):
    if not 'dojo_id' in request.session:
        return False
    elif not request.session['dojo_id']:
        return False
    else:
        return True

def landing_page(request):
    if not _is_hostname_configured(request):
        hostname = request.get_host().split(":")[0]
        return render(request, 'bad_configuration.html', {'hostname': hostname})

    dojo = Dojo.objects.get(id=request.session['dojo_id'])
    return render(request, 'landing_page.html', {'dojo': dojo})


def student_login(request):
    if not _is_hostname_configured(request):
        hostname = request.get_host().split(":")[0]
        return render(request, 'bad_configuration.html', {'hostname': hostname})

    if request.method == 'POST':
        form = EmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            student = Student.objects.filter(email=email).first()
            if not student:
                messages.error(request, f'Student with email "{email}"')
                return redirect('student_login')
            # the student is found
            session: SessionBase = request.session
            session['student_email'] = email
            return redirect('student_session')
    else:
        form = EmailForm()

    dojo = Dojo.objects.get(id=request.session['dojo_id'])
    return render(request, 'student/student_login.html', {'form': form, 'dojo': dojo})

def student_session(request):
    if not _is_hostname_configured(request):
        hostname = request.get_host().split(":")[0]
        return render(request, 'bad_configuration.html', {'hostname': hostname})

    if 'student_email' not in request.session:
        # session expired
        messages.error(request, f'Session expired')
        return redirect('student_login')

    student_email = request.session['student_email']
    student: Student = Student.objects.filter(email=student_email).first()

    # find the correct session
    future_sessions: Session = Session.objects.filter(
        dojo_id=student.dojo.id,
        date__gte=date.today()
    ).order_by('date')

    if not len(future_sessions):
        messages.error(request, f'No future sessions found. ')
        return redirect('student_login')

    future_session = future_sessions[0]
    sessions: Session = Session.objects.filter(
        dojo_id=student.dojo.id,
        date=future_session.date
    ).all()

    if len(sessions) == 1:
        # only one session in the day, we can redirect
        return redirect('student_session_id', session_id=sessions[0].pk)
    else:
        dojo = Dojo.objects.get(id=request.session['dojo_id'])
        return render(request, 'student/student_session_id.html', {
            'student': student,
            'sessions': sessions,
            'dojo': dojo,
            'date': future_session.date

        })

def student_session_id(request, session_id):

    session: Session = Session.objects.get(id=session_id)
    if not session:
        messages.error(request, f'Sessions not found')
        return redirect('student_login')

    if not 'student_email' in request.session:
        messages.error(request, f'Session expired. Please log in again.')
        return redirect('student_login')
    student_email = request.session['student_email']
    student: Student = Student.objects.filter(email=student_email).first()

    if not student:
        messages.error(request, f'Student not found. Please log in again.')
        return redirect('student_login')

    if session.event:
        address = session.event.address
    else:
        address = session.classes.address

    countdown_date = datetime.combine(session.date, session.time_from)

    # make sure that the membership is update.
    sales = Sale.objects.filter(
        dojo_id=student.dojo.pk,
        student_id=student.pk,
        date_from__lte=date.today(),
        date_to__gte=date.today(),
        membership__isnull=False
    )

    membership = None
    payment_required = False
    if not len(sales): # not active subscription
        membership = Membership.objects.filter(student_id=student.pk).first()
        payment_required = True
    elif sales[0].amount < sales[0].paid:  # not all the amount has been paid
        payment_required = True
        membership = MembershipProduct.objects.filter(student_id=student.pk).first()

    dojo = Dojo.objects.get(id=request.session['dojo_id'])
    return render(request, 'student/student_session_attendance.html', {
        'student': student,
        'session': session,
        'address':address,
        'countdown_date': countdown_date.isoformat(),
        'dojo': dojo,
        'membership': membership,
        'payment_required': payment_required

    })
def student_session_attendance(request):
    if not _is_hostname_configured(request):
        hostname = request.get_host().split(":")[0]
        return render(request, 'bad_configuration.html', {'hostname': hostname})

    session: SessionBase = request.session
    if not 'student_email' in session:
        messages.error(request, f'Session expired')
        return redirect('student_login')

    student_email = request.session['student_email']
    student: Student = Student.objects.filter(email=student_email).first()

    # TODO support more than 1 session per day
    class_session: Session = Session.objects.filter(
        dojo_id=student.dojo.id,
        date__gte=date.today()
    ).first()

    if not class_session:
        messages.error(request, f'The session does not exists.')
        return redirect('student_login')

    # is the student attendance already registered in this session ?
    attendance: Attendance = Attendance.objects.filter(student=student).first()

    if attendance:  # The student has already been registered for this session
        return redirect('student_session_attendance_completed')

    timezone = pytz.timezone(class_session.dojo.timezone.key)
    combined_datetime = datetime.combine(class_session.date, class_session.time_from)
    combined_datetime = timezone.localize(combined_datetime)
    thirty_minutes_from_now = datetime.now(timezone) + timedelta(minutes=30)

    if combined_datetime < thirty_minutes_from_now:
        Attendance.objects.create(
            dojo_id=class_session.dojo.id,
            session_id=class_session.id,
            date=class_session.date,
            duration=class_session.duration,
            student=student,
        )
        return redirect('student_session_attendance_completed')
    else:
        messages.error(request, f'it is too early to register for the session.')
        return redirect('student_login')

def student_session_attendance_complete(request):
    dojo = Dojo.objects.get(id=request.session['dojo_id'])
    return render(request, 'student/student_session_attendance_completed.html', {'dojo': dojo})