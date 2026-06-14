import base64
import logging
import urllib.parse
from datetime import datetime, date, timedelta
from typing import Any

import pytz
from django.contrib import messages
from django.contrib.sessions.backends.base import SessionBase
from django.contrib.sessions.backends.cache import SessionStore
from django.core.files.base import ContentFile
from django.shortcuts import render, redirect

from dojoconf.models import Dojo, Event
from financial.models import Sale, MembershipProduct, Membership
from shodan.models import Student, Session, Attendance, EventWaiver, StudentWaiver
from shodan.service import get_or_create_today_sessions
from web.forms import EmailForm, EventWaiverForm, KioskPinForm


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
    waiver_events = Event.objects.filter(
        dojo_id=dojo.id,
        requires_waiver=True,
        session__date__gte=date.today(),
    ).distinct()
    return render(request, 'landing_page.html', {'dojo': dojo, 'waiver_events': waiver_events})


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


def event_waiver_list(request):
    if not _is_hostname_configured(request):
        hostname = request.get_host().split(":")[0]
        return render(request, 'bad_configuration.html', {'hostname': hostname})

    dojo = Dojo.objects.get(id=request.session['dojo_id'])
    waiver_events = Event.objects.filter(
        dojo_id=dojo.id,
        requires_waiver=True,
        session__date__gte=date.today(),
    ).distinct()

    if len(waiver_events) == 0:
        return redirect('landing_page')

    if len(waiver_events) == 1:
        return redirect('event_waiver', event_id=waiver_events[0].id)

    return render(request, 'student/event_waiver_list.html', {
        'dojo': dojo, 'events': waiver_events
    })


def event_waiver(request, event_id):
    if not _is_hostname_configured(request):
        hostname = request.get_host().split(":")[0]
        return render(request, 'bad_configuration.html', {'hostname': hostname})

    dojo = Dojo.objects.get(id=request.session['dojo_id'])

    try:
        event = Event.objects.get(id=event_id, dojo_id=dojo.id)
    except Event.DoesNotExist:
        messages.error(request, 'Event not found.')
        return redirect('landing_page')

    future_session = Session.objects.filter(
        event_id=event_id,
        date__gte=date.today(),
    ).order_by('date', 'time_from').first()

    if request.method == 'POST':
        form = EventWaiverForm(request.POST)

        # Honeypot check — silently succeed for bots
        if form.data.get('email2'):
            request.session['waiver_event_id'] = event.id
            return redirect('event_waiver_success')

        if form.is_valid():
            email = form.cleaned_data['email']

            # Duplicate check
            existing = EventWaiver.objects.filter(event_id=event.id, email=email).first()
            if existing:
                messages.info(request, 'You have already signed the waiver for this event.')
                return render(request, 'student/event_waiver.html', {
                    'form': form, 'dojo': dojo, 'event': event, 'already_submitted': True,
                    'future_session': future_session,
                })

            # Build questionnaire responses dict
            questionnaire = {}
            for i in range(1, 15):
                questionnaire[f'q{i}'] = form.cleaned_data.get(f'q{i}')

            # Try to auto-match a student by email in this dojo
            student = Student.objects.filter(email=email, dojo_id=dojo.id).first()

            waiver = EventWaiver(
                dojo=dojo,
                event=event,
                student=student,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                address=form.cleaned_data['address'],
                suburb=form.cleaned_data.get('suburb'),
                state=form.cleaned_data.get('state'),
                post_code=form.cleaned_data.get('post_code'),
                phone=form.cleaned_data['phone'],
                email=email,
                date_of_birth=form.cleaned_data.get('date_of_birth'),
                current_grade=form.cleaned_data.get('current_grade'),
                emergency_contact_name=form.cleaned_data['emergency_contact_name'],
                emergency_contact_relationship=form.cleaned_data.get('emergency_contact_relationship'),
                emergency_contact_phone=form.cleaned_data['emergency_contact_phone'],
                terms_accepted=form.cleaned_data['terms_accepted'],
                questionnaire_responses=questionnaire,
                medical_specify=form.cleaned_data.get('q13_specify'),
                other_reason_specify=form.cleaned_data.get('q14_specify'),
                allergies=form.cleaned_data.get('allergies'),
                applicant_name=form.cleaned_data['applicant_name'],
                applicant_date=form.cleaned_data['applicant_date'],
                guardian_name=form.cleaned_data.get('guardian_name'),
                guardian_date=form.cleaned_data.get('guardian_date'),
            )
            waiver.save()

            # Save applicant signature
            sig_data = form.cleaned_data['applicant_signature_data']
            if ',' in sig_data:
                sig_data = sig_data.split(',', 1)[1]
            waiver.applicant_signature.save(
                'applicant_signature.png',
                ContentFile(base64.b64decode(sig_data)),
                save=True,
            )

            # Save guardian signature (optional)
            guardian_sig_data = form.cleaned_data.get('guardian_signature_data')
            if guardian_sig_data:
                if ',' in guardian_sig_data:
                    guardian_sig_data = guardian_sig_data.split(',', 1)[1]
                waiver.guardian_signature.save(
                    'guardian_signature.png',
                    ContentFile(base64.b64decode(guardian_sig_data)),
                    save=True,
                )

            request.session['waiver_event_id'] = event.id
            return redirect('event_waiver_success')
    else:
        form = EventWaiverForm()

    return render(request, 'student/event_waiver.html', {
        'form': form, 'dojo': dojo, 'event': event,
        'future_session': future_session,
    })


def event_waiver_success(request):
    dojo_id = request.session.get('dojo_id')
    dojo = Dojo.objects.get(id=dojo_id) if dojo_id else None

    event = None
    event_id = request.session.pop('waiver_event_id', None)
    if event_id:
        event = Event.objects.filter(id=event_id).first()

    return render(request, 'student/event_waiver_success.html', {
        'dojo': dojo,
        'success_message': event.waiver_success_message if event else None,
    })


def _kiosk_mode_active(request):
    return request.session.get('kiosk_mode', False)


KIOSK_MAX_ATTEMPTS = 10


def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def _send_kiosk_lock_alert(dojo, ip_address):
    from shodan.logging_matrix import send_matrix_message
    try:
        message = (
            f"\U0001F512 KIOSK LOCKED\n\n"
            f"Dojo: {dojo.name}\n"
            f"Failed PIN attempts: {dojo.kiosk_failed_attempts}\n"
            f"Last attempt IP: {ip_address}\n\n"
            f"An admin must unlock kiosk mode via the admin panel."
        )
        if not send_matrix_message(message):
            logging.warning("Matrix not configured; kiosk lock alert not sent.")
    except Exception as e:
        logging.error(f"Unable to send kiosk lock Matrix alert: {e}")


def _process_kiosk_pin(request, dojo, form):
    if form.data.get('website'):
        return 'honeypot'

    if dojo.kiosk_locked:
        return 'locked'

    if not form.is_valid():
        return 'invalid'

    pin = form.cleaned_data['pin']
    ip = _get_client_ip(request)

    if pin == dojo.kiosk_pin:
        if dojo.kiosk_failed_attempts > 0:
            dojo.kiosk_failed_attempts = 0
            dojo.save(update_fields=['kiosk_failed_attempts'])
        return 'success'

    dojo.kiosk_failed_attempts += 1
    dojo.save(update_fields=['kiosk_failed_attempts'])

    logger = logging.getLogger(__name__)
    logger.warning(
        "Failed kiosk PIN attempt for dojo '%s' from IP %s (attempt %d/%d)",
        dojo.name, ip, dojo.kiosk_failed_attempts, KIOSK_MAX_ATTEMPTS,
    )

    if dojo.kiosk_failed_attempts >= KIOSK_MAX_ATTEMPTS:
        dojo.kiosk_locked = True
        dojo.save(update_fields=['kiosk_locked'])
        _send_kiosk_lock_alert(dojo, ip)
        return 'locked'

    return 'wrong'


def kiosk_activate(request):
    if not _is_hostname_configured(request):
        hostname = request.get_host().split(":")[0]
        return render(request, 'bad_configuration.html', {'hostname': hostname})

    dojo = Dojo.objects.get(id=request.session['dojo_id'])

    if not dojo.kiosk_pin:
        messages.error(request, 'Kiosk mode is not configured. Set a Kiosk PIN in the admin first.')
        return redirect('landing_page')

    if dojo.kiosk_locked:
        return render(request, 'kiosk/kiosk_activate.html', {'dojo': dojo, 'locked': True})

    if request.method == 'POST':
        form = KioskPinForm(request.POST)
        result = _process_kiosk_pin(request, dojo, form)

        if result == 'honeypot':
            return render(request, 'kiosk/kiosk_fake_success.html')

        if result == 'locked':
            return render(request, 'kiosk/kiosk_activate.html', {'dojo': dojo, 'locked': True})

        if result == 'success':
            request.session['kiosk_mode'] = True
            sessions = get_or_create_today_sessions(dojo.id)
            if not sessions:
                messages.warning(request,
                    'No class scheduled for today. Students can still register as new students, '
                    'but attendance registration is unavailable. Create a session in the admin to enable it.')
            return redirect('kiosk_home')

        messages.error(request, 'Incorrect PIN.')
    else:
        form = KioskPinForm()

    return render(request, 'kiosk/kiosk_activate.html', {'form': form, 'dojo': dojo})


def kiosk_deactivate(request):
    if not _is_hostname_configured(request):
        return redirect('landing_page')

    dojo = Dojo.objects.get(id=request.session['dojo_id'])

    if dojo.kiosk_locked:
        return render(request, 'kiosk/kiosk_activate.html', {
            'dojo': dojo, 'locked': True, 'exit_mode': True,
        })

    if request.method == 'POST':
        form = KioskPinForm(request.POST)
        result = _process_kiosk_pin(request, dojo, form)

        if result == 'honeypot':
            return render(request, 'kiosk/kiosk_fake_success.html')

        if result == 'locked':
            return render(request, 'kiosk/kiosk_activate.html', {
                'dojo': dojo, 'locked': True, 'exit_mode': True,
            })

        if result == 'success':
            request.session['kiosk_mode'] = False
            return redirect('landing_page')

        messages.error(request, 'Incorrect PIN.')
    else:
        form = KioskPinForm()

    return render(request, 'kiosk/kiosk_activate.html', {
        'form': form, 'dojo': dojo, 'exit_mode': True,
    })


def kiosk_home(request):
    if not _is_hostname_configured(request):
        return redirect('landing_page')

    if not _kiosk_mode_active(request):
        return redirect('landing_page')

    request.session.pop('kiosk_waiver_pending_email', None)

    dojo = Dojo.objects.get(id=request.session['dojo_id'])
    has_sessions = Session.objects.filter(dojo_id=dojo.id, date=date.today()).exists()
    return render(request, 'kiosk/kiosk_home.html', {'dojo': dojo, 'has_sessions': has_sessions})


def kiosk_register(request):
    if not _is_hostname_configured(request) or not _kiosk_mode_active(request):
        return redirect('landing_page')

    dojo = Dojo.objects.get(id=request.session['dojo_id'])

    if request.method == 'POST':
        form = EventWaiverForm(request.POST)

        if form.data.get('email2'):
            return redirect('kiosk_register_success')

        if form.is_valid():
            email = form.cleaned_data['email']

            existing = Student.objects.filter(email=email, dojo_id=dojo.id).first()
            if existing:
                has_waiver = StudentWaiver.objects.filter(student=existing).exists()
                if has_waiver:
                    messages.info(request, f'A student with email "{email}" is already registered. Use "Register Attendance" to sign in.')
                    return render(request, 'kiosk/kiosk_register.html', {
                        'form': form, 'dojo': dojo, 'already_submitted': True,
                        'from_attendance': bool(request.session.get('kiosk_waiver_pending_email')),
                    })
                student = existing
            else:
                student = Student(
                    dojo=dojo,
                    status='active',
                    name=f"{form.cleaned_data['first_name']} {form.cleaned_data['last_name']}",
                    email=email,
                    mobile=form.cleaned_data['phone'],
                    date_of_birth=form.cleaned_data.get('date_of_birth'),
                    address1=form.cleaned_data['address'],
                    address2=' '.join(filter(None, [
                        form.cleaned_data.get('suburb', ''),
                        form.cleaned_data.get('state', ''),
                        form.cleaned_data.get('post_code', ''),
                    ])),
                    emergency_contact=' '.join(filter(None, [
                        form.cleaned_data['emergency_contact_name'],
                        form.cleaned_data.get('emergency_contact_relationship', ''),
                        form.cleaned_data['emergency_contact_phone'],
                    ])),
                    medical_conditions=' '.join(filter(None, [
                        f"Allergies: {form.cleaned_data.get('allergies', '')}" if form.cleaned_data.get('allergies') else '',
                        f"Medical: {form.cleaned_data.get('medical_specify', '')}" if form.cleaned_data.get('medical_specify') else '',
                    ])) or None,
                    start=date.today(),
                )

                grade = form.cleaned_data.get('current_grade', '')
                if grade and grade != 'black':
                    try:
                        student.kyu = int(grade.replace('kyu', ''))
                    except (ValueError, AttributeError):
                        pass
                elif grade == 'black':
                    student.dan = 1

                student.save()

            questionnaire = {}
            for i in range(1, 15):
                questionnaire[f'q{i}'] = form.cleaned_data.get(f'q{i}')

            waiver = StudentWaiver(
                dojo=dojo,
                student=student,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                address=form.cleaned_data['address'],
                suburb=form.cleaned_data.get('suburb'),
                state=form.cleaned_data.get('state'),
                post_code=form.cleaned_data.get('post_code'),
                phone=form.cleaned_data['phone'],
                email=email,
                date_of_birth=form.cleaned_data.get('date_of_birth'),
                current_grade=form.cleaned_data.get('current_grade'),
                emergency_contact_name=form.cleaned_data['emergency_contact_name'],
                emergency_contact_relationship=form.cleaned_data.get('emergency_contact_relationship'),
                emergency_contact_phone=form.cleaned_data['emergency_contact_phone'],
                terms_accepted=form.cleaned_data['terms_accepted'],
                questionnaire_responses=questionnaire,
                medical_specify=form.cleaned_data.get('q13_specify'),
                other_reason_specify=form.cleaned_data.get('q14_specify'),
                allergies=form.cleaned_data.get('allergies'),
                applicant_name=form.cleaned_data['applicant_name'],
                applicant_date=form.cleaned_data['applicant_date'],
                guardian_name=form.cleaned_data.get('guardian_name'),
                guardian_date=form.cleaned_data.get('guardian_date'),
            )
            waiver.save()

            sig_data = form.cleaned_data['applicant_signature_data']
            if ',' in sig_data:
                sig_data = sig_data.split(',', 1)[1]
            waiver.applicant_signature.save(
                'applicant_signature.png',
                ContentFile(base64.b64decode(sig_data)),
                save=True,
            )

            guardian_sig_data = form.cleaned_data.get('guardian_signature_data')
            if guardian_sig_data:
                if ',' in guardian_sig_data:
                    guardian_sig_data = guardian_sig_data.split(',', 1)[1]
                waiver.guardian_signature.save(
                    'guardian_signature.png',
                    ContentFile(base64.b64decode(guardian_sig_data)),
                    save=True,
                )

            is_post_attendance = 'kiosk_waiver_pending_email' in request.session
            request.session.pop('kiosk_waiver_pending_email', None)
            if is_post_attendance:
                request.session['kiosk_waiver_post_attendance'] = True
            return redirect('kiosk_register_success')
    else:
        pending_email = request.session.get('kiosk_waiver_pending_email')
        if pending_email:
            form = EventWaiverForm(initial={'email': pending_email})
        else:
            form = EventWaiverForm()

    return render(request, 'kiosk/kiosk_register.html', {
        'form': form, 'dojo': dojo,
        'from_attendance': bool(request.session.get('kiosk_waiver_pending_email')),
    })


def kiosk_register_success(request):
    if not _is_hostname_configured(request):
        return redirect('landing_page')

    dojo = Dojo.objects.get(id=request.session['dojo_id'])
    waiver_mode = request.session.pop('kiosk_waiver_post_attendance', False)
    return render(request, 'kiosk/kiosk_register_success.html', {
        'dojo': dojo, 'waiver_mode': waiver_mode,
    })


def kiosk_attendance(request):
    if not _is_hostname_configured(request) or not _kiosk_mode_active(request):
        return redirect('landing_page')

    dojo = Dojo.objects.get(id=request.session['dojo_id'])

    if request.method == 'POST':
        form = EmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            student = Student.objects.filter(email=email, dojo_id=dojo.id).first()
            if not student:
                messages.error(request, f'No student found with email "{email}". Please register as a new student first.')
                return redirect('kiosk_attendance')

            request.session['kiosk_student_email'] = email

            sessions = get_or_create_today_sessions(dojo.id)

            if not sessions:
                messages.error(request, 'No class scheduled for today. Please see your instructor.')
                return redirect('kiosk_attendance')

            if len(sessions) == 1:
                return _register_kiosk_attendance(request, student, sessions[0])

            return render(request, 'kiosk/kiosk_attendance_sessions.html', {
                'dojo': dojo, 'student': student, 'sessions': sessions,
            })
    else:
        form = EmailForm()

    return render(request, 'kiosk/kiosk_attendance.html', {'form': form, 'dojo': dojo})


def kiosk_attendance_session(request, session_id):
    if not _is_hostname_configured(request) or not _kiosk_mode_active(request):
        return redirect('landing_page')

    dojo = Dojo.objects.get(id=request.session['dojo_id'])
    student_email = request.session.get('kiosk_student_email')

    if not student_email:
        return redirect('kiosk_attendance')

    student = Student.objects.filter(email=student_email, dojo_id=dojo.id).first()
    if not student:
        return redirect('kiosk_attendance')

    session = Session.objects.filter(id=session_id, dojo_id=dojo.id, date=date.today()).first()
    if not session:
        messages.error(request, 'Session not found.')
        return redirect('kiosk_attendance')

    return _register_kiosk_attendance(request, student, session)


def _register_kiosk_attendance(request, student, session):
    existing = Attendance.objects.filter(student=student, session=session).first()
    if existing:
        messages.info(request, f'{student.name}, you are already registered for {session.name}.')
    else:
        Attendance.objects.create(
            dojo_id=session.dojo.id,
            session_id=session.id,
            date=session.date,
            duration=session.duration,
            student=student,
        )

    has_waiver = StudentWaiver.objects.filter(student=student).exists()
    if not has_waiver:
        request.session['kiosk_waiver_pending_email'] = student.email
        messages.warning(request, 'Attendance registered! Please complete the waiver form to finish.')
        return redirect('kiosk_register')

    return redirect('kiosk_attendance_completed')


def kiosk_attendance_completed(request):
    if not _is_hostname_configured(request):
        return redirect('landing_page')

    dojo = Dojo.objects.get(id=request.session['dojo_id'])
    request.session.pop('kiosk_student_email', None)
    return render(request, 'kiosk/kiosk_attendance_completed.html', {'dojo': dojo})


QUESTIONNAIRE_LABELS = {
    'q1': 'Heart condition or vascular disease',
    'q2': 'Chest pains',
    'q3': 'Recent chest pain',
    'q4': 'Faint / dizzy / loss of consciousness',
    'q5': 'High blood pressure',
    'q6': 'Medication for blood pressure / heart',
    'q7': 'Over 35/45, not accustomed to exercise',
    'q8': 'Bone or joint problem',
    'q9': 'Asthma',
    'q10': 'Respiratory problems',
    'q11': 'Diabetes',
    'q12': 'Epilepsy',
    'q13': 'Other illness',
    'q14': 'Other reason not to exercise',
}


def kiosk_attendees(request):
    if not _is_hostname_configured(request) or not _kiosk_mode_active(request):
        return redirect('landing_page')

    dojo = Dojo.objects.get(id=request.session['dojo_id'])

    if dojo.kiosk_locked:
        return render(request, 'kiosk/kiosk_attendees.html', {'dojo': dojo, 'locked': True})

    if request.method == 'POST':
        form = KioskPinForm(request.POST)
        result = _process_kiosk_pin(request, dojo, form)

        if result == 'honeypot':
            return render(request, 'kiosk/kiosk_fake_success.html')

        if result == 'locked':
            return render(request, 'kiosk/kiosk_attendees.html', {'dojo': dojo, 'locked': True})

        if result == 'success':
            request.session['kiosk_attendees_verified'] = True
            sessions = get_or_create_today_sessions(dojo.id)
            if not sessions:
                messages.error(request, 'No class scheduled for today.')
                return redirect('kiosk_attendees')
            if len(sessions) == 1:
                return redirect('kiosk_attendees_session', session_id=sessions[0].id)
            return render(request, 'kiosk/kiosk_attendees_sessions.html', {
                'dojo': dojo, 'sessions': sessions,
            })

        messages.error(request, 'Incorrect PIN.')
    else:
        form = KioskPinForm()

    return render(request, 'kiosk/kiosk_attendees.html', {'form': form, 'dojo': dojo})


def kiosk_attendees_session(request, session_id):
    if not _is_hostname_configured(request) or not _kiosk_mode_active(request):
        return redirect('landing_page')

    if not request.session.get('kiosk_attendees_verified'):
        return redirect('kiosk_attendees')

    dojo = Dojo.objects.get(id=request.session['dojo_id'])
    session = Session.objects.filter(id=session_id, dojo_id=dojo.id, date=date.today()).first()
    if not session:
        messages.error(request, 'Session not found.')
        return redirect('kiosk_attendees')

    attendances = Attendance.objects.filter(session=session).select_related('student')

    attendees = []
    for att in attendances:
        student = att.student
        waiver = StudentWaiver.objects.filter(student=student).first()

        if waiver:
            ec_name = waiver.emergency_contact_name
            ec_rel = waiver.emergency_contact_relationship or ''
            ec_phone = waiver.emergency_contact_phone

            medical_flags = []
            qr = waiver.questionnaire_responses or {}
            for q_key, label in QUESTIONNAIRE_LABELS.items():
                if qr.get(q_key) == 'yes':
                    medical_flags.append(label)

            allergies = waiver.allergies or ''
            medical_specify = waiver.medical_specify or ''
            has_waiver = True
        else:
            ec_name = student.emergency_contact or ''
            ec_rel = ''
            ec_phone = ''
            medical_flags = []
            if student.medical_conditions:
                medical_flags.append(student.medical_conditions)
            allergies = ''
            medical_specify = ''
            has_waiver = False

        has_medical = bool(medical_flags or allergies or medical_specify)

        attendees.append({
            'name': student.name,
            'ec_name': ec_name,
            'ec_rel': ec_rel,
            'ec_phone': ec_phone,
            'medical_flags': medical_flags,
            'allergies': allergies,
            'medical_specify': medical_specify,
            'has_medical': has_medical,
            'has_waiver': has_waiver,
        })

    attendees.sort(key=lambda a: a['name'])

    return render(request, 'kiosk/kiosk_attendees_list.html', {
        'dojo': dojo,
        'session': session,
        'attendees': attendees,
        'attendee_count': len(attendees),
    })