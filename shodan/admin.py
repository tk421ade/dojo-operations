from datetime import date

from django import forms
from django.contrib import admin, messages
from django.forms import Textarea, DateInput
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html, mark_safe

from dojoconf.admin import DojoFkFilterModelAdmin
from shodan.service import autocreate_sessions_for_dojo
from web.forms import QUESTIONNAIRE_QUESTIONS
from .models import *

QUESTIONNAIRE_LABELS = dict(QUESTIONNAIRE_QUESTIONS)



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
    # customers wants the date widget the signing up an student
    # formfield_overrides = {
    #     models.DateField: {'widget': DateInput}
    # }
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        # <a href="{reverse('admin:shodan_student_changelist')}">students</a>
        extra_context['documentation'] = \
            f"""<b>Help</b>: Students are individuals who practice karate. 
            They access training <a href="{reverse('admin:shodan_session_changelist')}">sessions</a> 
            through a <a href="{reverse('admin:financial_membership_changelist')}">membership subscription</a>."""

        # enable 'status: active' by default (TODO disables listing all students, minor inconvenient)
        if not request.GET:
            q = request.GET.copy()
            q['status__exact'] = 'active'  # assuming 'active' is the value for active students
            request.GET = q
            request.META['QUERY_STRING'] = request.GET.urlencode()

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


class WaiverAdminBase(DojoFkFilterModelAdmin):

    formfield_overrides = {
        models.JSONField: {'widget': Textarea(attrs={'rows': 14, 'class': 'vLargeTextField'})},
    }

    def applicant_signature_image(self, obj):
        if obj and obj.applicant_signature:
            return format_html(
                '<img src="{}" style="max-width:400px; border:1px solid #ccc; border-radius:4px;" />',
                obj.applicant_signature.url)
        return '(no signature)'
    applicant_signature_image.short_description = 'Current Signature'

    def guardian_signature_image(self, obj):
        if obj and obj.guardian_signature:
            return format_html(
                '<img src="{}" style="max-width:400px; border:1px solid #ccc; border-radius:4px;" />',
                obj.guardian_signature.url)
        return '(no signature)'
    guardian_signature_image.short_description = 'Current Signature'

    def questionnaire_display(self, obj):
        if not obj:
            return '(none)'
        responses = obj.questionnaire_responses or {}
        if not responses:
            return '(none)'
        rows = []
        for key, label in QUESTIONNAIRE_QUESTIONS:
            answer = responses.get(key)
            if answer is None:
                continue
            color = '#c62828' if answer == 'yes' else '#2e7d32'
            rows.append(format_html(
                '<tr>'
                '<td style="padding:6px 12px 6px 0; border-bottom:1px solid #eee;">{}</td>'
                '<td style="padding:6px 0; border-bottom:1px solid #eee; font-weight:bold; color:{}; text-align:center;">{}</td>'
                '</tr>',
                label, color, answer.capitalize(),
            ))
        return mark_safe(
            '<table style="border-collapse:collapse; font-size:13px;">'
            '<thead><tr>'
            '<th style="padding:6px 12px 6px 0; border-bottom:2px solid #ddd; text-align:left;">Question</th>'
            '<th style="padding:6px 0; border-bottom:2px solid #ddd; text-align:center;">Answer</th>'
            '</tr></thead>'
            '<tbody>{}</tbody></table>'
            .format(''.join(rows))
        )
    questionnaire_display.short_description = 'Responses'

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Applicant'


class EventWaiverAdmin(WaiverAdminBase):
    list_display = ('id', 'full_name', 'event__name', 'email', 'applicant_date', 'created_at')
    list_display_links = ('id', 'full_name')
    list_filter = ('event',)
    search_fields = ('first_name', 'last_name', 'email')
    readonly_fields = (
        'created_at', 'updated_at', 'deleted_at',
        'dojo', 'event', 'student',
        'first_name', 'last_name', 'address', 'suburb', 'state', 'post_code',
        'phone', 'email', 'date_of_birth', 'current_grade',
        'emergency_contact_name', 'emergency_contact_relationship', 'emergency_contact_phone',
        'terms_accepted',
        'questionnaire_display', 'medical_specify', 'other_reason_specify', 'allergies',
        'applicant_signature_image', 'applicant_name', 'applicant_date',
        'guardian_signature_image', 'guardian_name', 'guardian_date',
    )
    fieldsets = (
        ('Personal Information', {
            'fields': ('dojo', 'event', 'student',
                       'first_name', 'last_name', 'address', 'suburb', 'state', 'post_code',
                       'phone', 'email', 'date_of_birth', 'current_grade'),
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_relationship', 'emergency_contact_phone'),
        }),
        ('Terms & Conditions', {
            'fields': ('terms_accepted',),
        }),
        ('Physical Readiness Questionnaire', {
            'fields': ('questionnaire_display', 'medical_specify', 'other_reason_specify', 'allergies'),
        }),
        ('Edit Questionnaire Responses (Raw JSON)', {
            'fields': ('questionnaire_responses',),
            'classes': ('collapse',),
            'description': 'Edit the raw JSON questionnaire data. Format: {"q1": "yes", "q2": "no", ...}',
        }),
        ('Applicant Signature', {
            'fields': ('applicant_signature_image', 'applicant_name', 'applicant_date'),
        }),
        ('Replace Applicant Signature', {
            'fields': ('applicant_signature',),
            'classes': ('collapse',),
            'description': 'Upload a new signature image to replace the current one.',
        }),
        ('Guardian Signature', {
            'fields': ('guardian_signature_image', 'guardian_name', 'guardian_date'),
        }),
        ('Replace Guardian Signature', {
            'fields': ('guardian_signature',),
            'classes': ('collapse',),
            'description': 'Upload a new guardian signature image to replace the current one.',
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',),
        }),
    )

    def event__name(self, obj):
        return obj.event.name
    event__name.short_description = 'Event'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['documentation'] = \
            f"""<b>Help</b>: Event waivers are participation forms signed by students (including external students from other dojos) 
            for specific <a href="{reverse('admin:dojoconf_event_changelist')}">events</a>. 
            Each record contains personal info, medical questionnaire responses, and digital signatures."""
        return super().changelist_view(request, extra_context)


class StudentWaiverAdmin(WaiverAdminBase):
    list_display = ('id', 'full_name', 'student__name', 'email', 'applicant_date', 'created_at')
    list_display_links = ('id', 'full_name')
    search_fields = ('first_name', 'last_name', 'email', 'student__name')
    readonly_fields = (
        'created_at', 'updated_at', 'deleted_at',
        'dojo', 'student',
        'first_name', 'last_name', 'address', 'suburb', 'state', 'post_code',
        'phone', 'email', 'date_of_birth', 'current_grade',
        'emergency_contact_name', 'emergency_contact_relationship', 'emergency_contact_phone',
        'terms_accepted',
        'questionnaire_display', 'medical_specify', 'other_reason_specify', 'allergies',
        'applicant_signature_image', 'applicant_name', 'applicant_date',
        'guardian_signature_image', 'guardian_name', 'guardian_date',
    )
    fieldsets = (
        ('Personal Information', {
            'fields': ('dojo', 'student',
                       'first_name', 'last_name', 'address', 'suburb', 'state', 'post_code',
                       'phone', 'email', 'date_of_birth', 'current_grade'),
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_relationship', 'emergency_contact_phone'),
        }),
        ('Terms & Conditions', {
            'fields': ('terms_accepted',),
        }),
        ('Physical Readiness Questionnaire', {
            'fields': ('questionnaire_display', 'medical_specify', 'other_reason_specify', 'allergies'),
        }),
        ('Edit Questionnaire Responses (Raw JSON)', {
            'fields': ('questionnaire_responses',),
            'classes': ('collapse',),
            'description': 'Edit the raw JSON questionnaire data. Format: {"q1": "yes", "q2": "no", ...}',
        }),
        ('Applicant Signature', {
            'fields': ('applicant_signature_image', 'applicant_name', 'applicant_date'),
        }),
        ('Replace Applicant Signature', {
            'fields': ('applicant_signature',),
            'classes': ('collapse',),
            'description': 'Upload a new signature image to replace the current one.',
        }),
        ('Guardian Signature', {
            'fields': ('guardian_signature_image', 'guardian_name', 'guardian_date'),
        }),
        ('Replace Guardian Signature', {
            'fields': ('guardian_signature',),
            'classes': ('collapse',),
            'description': 'Upload a new guardian signature image to replace the current one.',
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',),
        }),
    )

    def student__name(self, obj):
        return obj.student.name if obj.student else '(none)'
    student__name.short_description = 'Student'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['documentation'] = \
            f"""<b>Help</b>: Student waivers are registration forms signed by new students via Kiosk Mode. 
            Each record contains personal info, medical questionnaire responses, and digital signatures. 
            The linked <a href="{reverse('admin:shodan_student_changelist')}">student</a> record is created automatically."""
        return super().changelist_view(request, extra_context)


# Admin-editable models

admin.site.register(Student, StudentAdmin)
admin.site.register(Session, SessionAdmin)
admin.site.register(Attendance, AttendanceAdmin)
admin.site.register(EventWaiver, EventWaiverAdmin)
admin.site.register(StudentWaiver, StudentWaiverAdmin)

