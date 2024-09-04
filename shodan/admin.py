import logging
from datetime import date

from dateutil.relativedelta import relativedelta
from django.contrib import admin, messages
from django.forms import TimeField
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import path, reverse

from dojoconf.admin import DojoFkFilterModelAdmin
from .forms import AdminSessionForm
from .models import *


class StudentAdmin(DojoFkFilterModelAdmin):
    list_display = ('id', 'dojo__name', 'name', 'status', 'kyu', 'dan')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')
    list_display_links = ('id', 'name')
    list_filter = ('status',)
    search_fields = ('name',)
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        # <a href="{reverse('admin:shodan_student_changelist')}">students</a>
        extra_context['documentation'] = \
            f"""<b>help</b>: Students is an individual that practices karate. 
            They train in <a href="{reverse('admin:shodan_session_changelist')}">sessions</a> by 
            <a href="{reverse('admin:financial_membership_changelist')}">subscribing</a> to a 
            <a href="{reverse('admin:financial_membershipproduct_changelist')}">product</a>. """
        return super().changelist_view(request, extra_context)


class SessionAdmin(DojoFkFilterModelAdmin):
    change_list_template = 'admin/shodan/session/change_list.html'
    list_display = ('id', 'name', 'date', 'time_from', 'time_to', 'duration' )
    list_display_links = ('id', 'name')
    search_fields = ('id', 'name',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')
    list_filter = ('date',)
    date_hierarchy = "date"
    #form = AdminSessionForm

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('date')

    def changelist_view(self, request, extra_context=None):
        """

        If there are no extra filter parameters, display the most recent sessions first

        :param request:
        :param extra_context:
        :return:
        """
        extra_context = extra_context or {}

        # TODO there is a bug here.

        qs = self.get_queryset(request)
        future_qs = qs.filter(date__gte=date.today())
        past_qs = qs.filter(date__lt=date.today())
        combined_qs = list(future_qs) + list(past_qs)
        self.queryset = combined_qs

        extra_context['documentation'] = \
            f"""<b>help</b>: Session are training opportunities created from 
            <a href="{reverse('admin:dojoconf_classes_changelist')}">classes</a> and 
            <a href="{reverse('admin:dojoconf_event_changelist')}">events</a>. 
            You track the <a href="{reverse('admin:shodan_student_changelist')}">students</a> that 
            <a href="{reverse('admin:shodan_attendance_changelist')}">attended</a> the session. 
            <a href="{reverse('admin:shodan_student_changelist')}">Students</a> can register the 
            <a href="{reverse('admin:shodan_attendance_changelist')}">attendance</a> automatically.  
            Additionally, you can generate sessions automatically from <a href="{reverse('admin:dojoconf_classes_changelist')}">classes</a> 
            by clicking the button 'Create Sessions Automatically'. """
        return super().changelist_view(request, extra_context)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('autosession/', self.admin_site.admin_view(self.autosession), name='shodan_session_autosession'),
        ]
        return custom_urls + urls

    def autosession(self, request):

        weekday_mapping = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6
        }

        # Your Python code here
        dojo_id = request.session.get('dojo_id')
        all_classes = Classes.objects.filter(dojo_id=dojo_id)
        for classes in all_classes:
            current_date = classes.interval.starting_at
            if current_date < datetime.now().date():
                current_date = datetime.now().date()
            finishing_date = datetime.now().date() + relativedelta(months=1)
            if classes.interval.finishing_at and finishing_date > classes.interval.finishing_at:
                finishing_date = classes.interval.finishing_at

            logging.warning(f"Calculating all working days from {current_date} to {finishing_date}")
            days_of_week = classes.interval.days_of_week
            already_exists_count = 0
            new_count = 0
            while current_date <= finishing_date:
                for day in days_of_week:
                    if day in weekday_mapping:
                        if current_date.weekday() == weekday_mapping[day]:
                            logging.warning(f"Creating Session")

                            # check if the session already exists
                            sessions = Session.objects.filter(
                                date=current_date,
                                dojo_id=classes.dojo.pk,
                                classes_id=classes.pk
                            )
                            if sessions.exists():
                                already_exists_count += 1
                            else:
                                new_count += 1
                                Session.objects.create(
                                    dojo_id=classes.dojo.pk,
                                    classes_id=classes.pk,
                                    date=current_date,
                                )
                    else:
                        logging.warning(f"{day} not found at interval {classes.interval}")

                current_date += timedelta(days=1)

            if new_count:
                messages.success(request, f"Processing Classes {classes.name}: {new_count} sessions created from {current_date} to {finishing_date}")
            if already_exists_count:
                messages.success(request, f"Processing Classes {classes.name}: {already_exists_count} sessions already existed from {current_date} to {finishing_date}")

        if not all_classes:
            messages.warning(request, f"Nothing to process. Have you configured Classes yet ?")

        return redirect(reverse('admin:shodan_session_changelist'))


class AttendanceAdmin(DojoFkFilterModelAdmin):
    list_display = ('id', 'date', 'student__name','session__name', 'duration', 'points')
    list_display_links = ('id', 'student__name')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')
    search_fields = ('student__name', 'session__name')
    autocomplete_fields = ["student", "dojo"]
    list_filter = ('date',)
    date_hierarchy = "date"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        attendance_doc = ""
        if request.session.has_key('dojo_id'):
            dojo_id = request.session.get('dojo_id')
            dojo = Dojo.objects.get(id=dojo_id)
            attendance_doc = f"  Students can register the attendance via <a href='https://{dojo.hostname}'>{dojo.hostname}</a>."

        extra_context['documentation'] = \
            f"""<b>help</b>: Attendance tracks the <a href="{reverse('admin:shodan_student_changelist')}">students</a> 
            that has trained in a <a href="{reverse('admin:shodan_session_changelist')}">session</a>. {attendance_doc}"""
        return super().changelist_view(request, extra_context)

# Admin-editable models

admin.site.register(Student, StudentAdmin)
admin.site.register(Session, SessionAdmin)
admin.site.register(Attendance, AttendanceAdmin)

