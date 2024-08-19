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


class SessionAdmin(DojoFkFilterModelAdmin):
    change_list_template = 'admin/shodan/session/change_list.html'
    list_display = ('id', 'date', 'name')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')
    list_filter = ('date',)
    #form = AdminSessionForm

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('date')

    def changelist_view(self, request, extra_context=None):
        qs = self.get_queryset(request)
        future_qs = qs.filter(date__gte=date.today())
        past_qs = qs.filter(date__lt=date.today())
        combined_qs = list(future_qs) + list(past_qs)
        self.queryset = combined_qs
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
        all_classes = Classes.objects.all()
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
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')
    search_fields = ('student__name', 'session__name')
    list_filter = ('date',)


# Admin-editable models

admin.site.register(Student, StudentAdmin)
admin.site.register(Session, SessionAdmin)
admin.site.register(Attendance, AttendanceAdmin)

