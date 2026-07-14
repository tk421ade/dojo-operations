from datetime import date

from django import forms
from django.contrib import admin, messages
from django.forms import Textarea, DateInput
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html, mark_safe

from dojoconf.admin import DojoFkFilterModelAdmin
from shodan.service import autocreate_sessions_for_dojo
from web.forms import QUESTIONNAIRE_QUESTIONS, DEFAULT_FEEDBACK_QUESTIONS
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
    actions = ['generate_feedback_link']
    #form = AdminSessionForm

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('-date')

    def changelist_view(self, request, extra_context=None):
        """

        Display future sessions first (nearest upcoming first), then past sessions
        (most recent first).

        """
        extra_context = extra_context or {}

        qs = super().get_queryset(request)
        future_qs = qs.filter(date__gte=date.today()).order_by('date')
        past_qs = qs.filter(date__lt=date.today()).order_by('-date')
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

    @admin.action(description='Generate feedback link')
    def generate_feedback_link(self, request, queryset):
        created = 0
        skipped = 0
        urls = []
        for session in queryset:
            existing = SessionFeedbackLink.objects.filter(session=session).first()
            if existing:
                skipped += 1
                continue
            link = SessionFeedbackLink.objects.create(
                dojo=session.dojo,
                session=session,
            )
            for q in DEFAULT_FEEDBACK_QUESTIONS:
                SessionFeedbackQuestion.objects.create(
                    feedback_link=link,
                    question_text=q['question_text'],
                    question_type=q['question_type'],
                    choices=q['choices'],
                    order=q['order'],
                    required=q['required'],
                )
            created += 1
            host = session.dojo.hostname or request.get_host().split(":")[0]
            url = f"https://{host}/feedback/{link.token}"
            urls.append(f"{session.name}: {url}")

        if created:
            self.message_user(request, f'Generated {created} feedback link(s).', level=messages.SUCCESS)
            for url in urls:
                self.message_user(request, url, level=messages.INFO)
        if skipped:
            self.message_user(request, f'{skipped} session(s) already had a feedback link (skipped).', level=messages.WARNING)

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


class SessionFeedbackQuestionInline(admin.TabularInline):
    model = SessionFeedbackQuestion
    extra = 0
    ordering = ('order',)


class SessionFeedbackLinkAdmin(DojoFkFilterModelAdmin):
    list_display = ('id', 'session__name', 'is_active', 'question_count', 'response_count', 'created_at')
    list_display_links = ('id', 'session__name')
    search_fields = ('session__name', 'token')
    list_filter = ('is_active',)
    readonly_fields = ('token', 'feedback_url', 'created_at', 'updated_at', 'deleted_at')
    autocomplete_fields = ['session']
    actions = ['populate_default_questions']
    inlines = [SessionFeedbackQuestionInline]

    fieldsets = (
        (None, {
            'fields': ('dojo', 'session', 'is_active'),
        }),
        ('Feedback URL', {
            'fields': ('token', 'feedback_url'),
            'description': 'Share this URL manually (email, QR code, etc.). It is not linked from any page in the application.',
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change and obj.questions.count() == 0:
            for q in DEFAULT_FEEDBACK_QUESTIONS:
                SessionFeedbackQuestion.objects.create(
                    feedback_link=obj,
                    question_text=q['question_text'],
                    question_type=q['question_type'],
                    choices=q['choices'],
                    order=q['order'],
                    required=q['required'],
                )
            messages.info(request, 'Default feedback questions have been added. You can edit them below.')

    @admin.action(description='Populate default questions')
    def populate_default_questions(self, request, queryset):
        existing_texts = set()
        added = 0
        for link in queryset:
            existing = set(link.questions.values_list('question_text', flat=True))
            for q in DEFAULT_FEEDBACK_QUESTIONS:
                if q['question_text'] not in existing:
                    SessionFeedbackQuestion.objects.create(
                        feedback_link=link,
                        question_text=q['question_text'],
                        question_type=q['question_type'],
                        choices=q['choices'],
                        order=q['order'],
                        required=q['required'],
                    )
                    added += 1
        self.message_user(request, f'Added {added} default question(s).', level=messages.SUCCESS)

    def session__name(self, obj):
        return obj.session.name
    session__name.short_description = 'Session'

    def feedback_url(self, obj):
        host = obj.dojo.hostname or ''
        if host:
            return format_html(
                '<a href="https://{}/feedback/{}" target="_blank" rel="noopener noreferrer">https://{}/feedback/{}</a>',
                host, obj.token, host, obj.token)
        return f'/feedback/{obj.token}'
    feedback_url.short_description = 'Feedback URL'

    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = 'Questions'

    def response_count(self, obj):
        return obj.submissions.count()
    response_count.short_description = 'Responses'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['documentation'] = \
            f"""<b>Help</b>: Feedback links are generated from individual
            <a href="{reverse('admin:shodan_session_changelist')}">sessions</a> via the
            'Generate feedback link' admin action. Each link has an unguessable random URL.
            Questions can be customised per session using the inline below."""
        return super().changelist_view(request, extra_context)


class SessionFeedbackAdmin(DojoFkFilterModelAdmin):
    list_display = ('id', 'session_name', 'created_at')
    list_display_links = ('id',)
    search_fields = ('feedback_link__session__name',)
    list_filter = ('created_at',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'dojo', 'feedback_link', 'responses_display')

    fieldsets = (
        (None, {
            'fields': ('dojo', 'feedback_link'),
        }),
        ('Responses', {
            'fields': ('responses_display',),
        }),
        ('Raw Responses (JSON)', {
            'fields': ('responses',),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def session_name(self, obj):
        return obj.feedback_link.session.name
    session_name.short_description = 'Session'

    def responses_display(self, obj):
        if not obj or not obj.responses:
            return '(none)'
        questions = {q.pk: q for q in obj.feedback_link.questions.all()}
        rows = []
        for q_pk, answer in obj.responses.items():
            question = questions.get(int(q_pk))
            label = question.question_text if question else f'(deleted question {q_pk})'
            rows.append(format_html(
                '<tr>'
                '<td style="padding:6px 12px 6px 0; border-bottom:1px solid #eee; max-width:400px;">{}</td>'
                '<td style="padding:6px 0; border-bottom:1px solid #eee; font-weight:bold;">{}</td>'
                '</tr>',
                label, answer,
            ))
        return mark_safe(
            '<table style="border-collapse:collapse; font-size:13px;">'
            '<thead><tr>'
            '<th style="padding:6px 12px 6px 0; border-bottom:2px solid #ddd; text-align:left;">Question</th>'
            '<th style="padding:6px 0; border-bottom:2px solid #ddd; text-align:left;">Answer</th>'
            '</tr></thead>'
            '<tbody>{}</tbody></table>'
            .format(''.join(rows))
        )
    responses_display.short_description = 'Responses'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['documentation'] = \
            f"""<b>Help</b>: Anonymous feedback submissions collected via public feedback URLs.
            Each record contains responses to the questions configured on the
            <a href="{reverse('admin:shodan_sessionfeedbacklink_changelist')}">feedback link</a>.
            No student identity is stored — all submissions are fully anonymous."""
        return super().changelist_view(request, extra_context)


admin.site.register(SessionFeedbackLink, SessionFeedbackLinkAdmin)
admin.site.register(SessionFeedback, SessionFeedbackAdmin)

