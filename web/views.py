from datetime import datetime, date
from typing import Any

from django.contrib import messages
from django.contrib.sessions.backends.base import SessionBase
from django.contrib.sessions.backends.cache import SessionStore
from django.shortcuts import render, redirect

from shodan.models import Student, Session
from web.forms import EmailForm


# Create your views here.
def landing_page(request):
    if request.method == 'POST':
        form = EmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            student = Student.objects.filter(email=email).first()
            if not student:
                messages.error(request, f'Student with email "{email}"')
                return redirect('landing_page')
            # save the email
            session: SessionBase = request.session
            session['student_email'] = email
            return redirect('session_finder')
    else:
        form = EmailForm()
    return render(request, 'landing_page.html', {'form': form})


def session_finder(request):

    if 'student_email' not in request.session:
        # session expired
        return redirect('landing_page')

    student_email = request.session['student_email']
    student: Student = Student.objects.filter(email=student_email).first()
    session: Session = Session.objects.filter(
        dojo_id=student.dojo.id,
        date__gte=date.today()
    ).first()

    if not session:
        messages.error(request, f'Sessions not found')

    if session.event:
        address = session.event.address
    else:
        address = session.classes.address

    countdown_date = datetime.combine(session.date, session.time_from)
    address.latitude
    address.longitude

    return render(request, 'session_finder.html', {
        'session': session,
        'address':address,
        'countdown_date': countdown_date.isoformat()
    } )