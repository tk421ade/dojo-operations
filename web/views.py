from datetime import datetime, date, timedelta
from typing import Any

import pytz
from django.contrib import messages
from django.contrib.sessions.backends.base import SessionBase
from django.contrib.sessions.backends.cache import SessionStore
from django.shortcuts import render, redirect

from shodan.models import Student, Session, Attendance
from web.forms import EmailForm


# Create your views here.
def landing_page(request):
    return render(request, 'landing_page.html')


def student_login(request):
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
    return render(request, 'student/student_login.html', {'form': form})

def student_session(request):

    if 'student_email' not in request.session:
        # session expired
        messages.error(request, f'Session expired')
        return redirect('student_login')

    student_email = request.session['student_email']
    student: Student = Student.objects.filter(email=student_email).first()
    sessions: Session = Session.objects.filter(
        dojo_id=student.dojo.id,
        date__gte=date.today()
    )
    if not len(sessions):
        messages.error(request, f'No future classes found. ')
        return redirect('student_login')
    else:
        session = sessions[0]


    if not session:
        messages.error(request, f'Sessions not found')

    if session.event:
        address = session.event.address
    else:
        address = session.classes.address

    countdown_date = datetime.combine(session.date, session.time_from)

    today_sessions: Session = Session.objects.filter(
        dojo_id=student.dojo.id,
        date=date.today()
    )
    if len(today_sessions) > 1:
        messages.error(request, f'There are multiple sessions today, and the automatic attendance '
                                f'registration does not support this (yet).')

    return render(request, 'student/student_session_attendance.html', {
            'student': student,
            'session': session,
            'address':address,
            'countdown_date': countdown_date.isoformat()
        })

def student_session_attendance(request):
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

    if attendance:
        messages.error(request, f'You have already registered for this session')
        return redirect('student_login')

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
    return render(request, 'student/student_session_attendance_completed.html')