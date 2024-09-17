from datetime import date

from django import forms
from django.contrib import admin, messages
from django.forms import Textarea, DateInput
from django.shortcuts import redirect
from django.urls import path, reverse

from dojoconf.admin import DojoFkFilterModelAdmin
from shodan.service import autocreate_sessions_for_dojo
from .models import *



class StudentDocumentInlineAdmin(admin.TabularInline):
    model = StudentDocument
    extra = 1
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'class': 'wide-textarea'})},
    }


class StudentAdmin(DojoFkFilterModelAdmin):
    list_display = ('id', 'dojo__name', 'name', 'status', 'kyu', 'dan')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')
    list_display_links = ('id', 'name')
    list_filter = ('status',)
    search_fields = ('name',)
    inlines = [StudentDocumentInlineAdmin]
    formfield_overrides = {
        models.DateField: {'widget': DateInput}
    }
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        # <a href="{reverse('admin:shodan_student_changelist')}">students</a>
        extra_context['documentation'] = \
            f"""<b>Help</b>: Students are individuals who practice karate. 
            They access training <a href="{reverse('admin:shodan_session_changelist')}">sessions</a> 
            through a <a href="{reverse('admin:financial_membership_changelist')}">membership subscription</a>."""
        return super().changelist_view(request, extra_context)

    def get_form(self, request, obj=None, **kwargs):
        form =  super().get_form(request, obj, **kwargs)
        form.base_fields['date_of_birth'].widget.attrs['placeholder'] = "YYYY-MM-DD"
        form.base_fields['start'].widget.attrs['placeholder'] = "YYYY-MM-DD"
        return form


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
            f"""<b>Help</b>: Sessions represent training opportunities derived from 
            <a href="{reverse('admin:dojoconf_classes_changelist')}">classes</a> and 
            <a href="{reverse('admin:dojoconf_event_changelist')}">events</a>. 
            <a href="{reverse('admin:shodan_attendance_changelist')}">Attendance</a> tracking is available for each session, 
            with registration options for <a href="{reverse('admin:shodan_student_changelist')}">students</a>. 
            Furthermore, sessions can be automatically generated from <a href="{reverse('admin:dojoconf_classes_changelist')}">classes</a> 
            by using the 'Create Sessions Automatically' feature. """

        return super().changelist_view(request, extra_context)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('autosession/', self.admin_site.admin_view(self.autosession), name='shodan_session_autosession'),
        ]
        return custom_urls + urls

    def autosession(self, request):


        # Your Python code here

        dojos = Dojo.objects.filter(users__username=request.user.username)

        if not dojos:
            messages.warning(request, f"Nothing to process. Is user '{request.user.username}' associated to dojos?")
            return redirect(reverse('admin:shodan_session_changelist'))

        classes_processed = 0
        for dojo in dojos:
            classes_processed += autocreate_sessions_for_dojo(request, dojo.pk)

        if not classes_processed:
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
            if dojo_id:
                dojo = Dojo.objects.get(id=dojo_id)
                attendance_doc = f"Students can log their attendance online via <a href='https://{dojo.hostname}'>{dojo.hostname}</a>."

        extra_context['documentation'] = \
            f"""<b>Help</b>:  The Attendance feature tracks <a href="{reverse('admin:shodan_student_changelist')}">student</a> 
            participation in <a href="{reverse('admin:shodan_session_changelist')}">sessions</a>. {attendance_doc}"""

        return super().changelist_view(request, extra_context)

# Admin-editable models

admin.site.register(Student, StudentAdmin)
admin.site.register(Session, SessionAdmin)
admin.site.register(Attendance, AttendanceAdmin)

