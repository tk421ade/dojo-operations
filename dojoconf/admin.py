from typing import Any

from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.sessions.backends.cache import SessionStore
from django.urls import reverse

from dojoconf.models import Dojo, Address, Classes, Event


class DojoFkFilterModelAdmin(admin.ModelAdmin):

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Only display in the FK the dojos that the user has access to
        """
        if db_field.name == 'dojo':
            if not request.user.is_superuser:
                dojo_ids = request.session.get('user_dojos', [])
                kwargs['queryset'] = Dojo.objects.filter(id__in=dojo_ids)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_changeform_initial_data(self, request):
        """
        Select the first dojo as default when adding more rows
        """
        initial = super().get_changeform_initial_data(request)
        if not request.user.is_superuser:
            dojo_ids = request.session.get('user_dojos', [])
            if dojo_ids:
                initial['dojo'] = dojo_ids[0]
        return initial

    def get_search_results(self, request, queryset, search_term):
        """ Make sure that search results are properly filtered """
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if not request.user.is_superuser:
            dojo_ids = request.session.get('user_dojos', [])
            if queryset.model._meta.get_field('dojo'):
                queryset = queryset.filter(dojo__in=dojo_ids)
        return queryset, use_distinct

    def has_change_permission(self, request, obj=None):
        """ Forbid users to change permissions of objects that they don't own """
        if not request.user.is_superuser:
            dojo = getattr(obj, 'dojo', None)
            dojo_ids = request.session.get('user_dojos', [])
            if obj and dojo and obj.dojo.id not in dojo_ids:
                return False

        return super().has_change_permission(request, obj)

    def has_view_permission(self, request, obj=None):
        """ Forbid users to view permissions of objects that they don't own """
        if not request.user.is_superuser:
            dojo = getattr(obj, 'dojo', None)
            dojo_ids = request.session.get('user_dojos', [])
            if obj and dojo and obj.dojo.id not in dojo_ids:
                return False
        return super().has_view_permission(request, obj)

    def created_at_tz(self, obj):
        if obj.created_at and obj.dojo:
            return obj.created_at.astimezone(obj.dojo.timezone).strftime('%Y-%m-%d %H:%M:%S')

# Register your models here.
class DojoAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'timezone')
    list_display_links = ('id', 'name')
    search_fields = ('id', 'name',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at', 'kiosk_failed_attempts')
    autocomplete_fields = ["users"]
    actions = ['unlock_kiosk']
    fieldsets = (
        (None, {
            'fields': ('name', 'email', 'users', 'timezone', 'hostname')
        }),
        ('Kiosk Mode', {
            'fields': ('kiosk_pin', 'kiosk_locked', 'kiosk_failed_attempts'),
            'classes': ('collapse',),
            'description': 'Set a 4-6 digit PIN to enable Kiosk Mode on the student-facing landing page. After 10 failed PIN attempts the kiosk locks and must be unlocked here.',
        }),
        ('Branding', {
            'fields': ('logo',),
            'classes': ('collapse',),
            'description': 'Upload a dojo logo (transparent PNG designed for white background). Displayed on all public pages.',
        }),
        ('Footer & Privacy', {
            'fields': ('privacy_policy_url',),
            'classes': ('collapse',),
            'description': 'Optional external URL to the dojo privacy policy. When set, a "Privacy Policy" link is shown in the public site footer alongside the copyright notice.',
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',),
        }),
    )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        # <a href="{reverse('admin:shodan_session_changelist')}">session</a>
        extra_context['documentation'] = \
            f"""<b>Help</b>: The Dojo is the entity responsible for organizing 
            and hosting training 
            <a href="{reverse('admin:shodan_session_changelist')}">sessions</a> 
            and <a href="{reverse('admin:dojoconf_event_changelist')}">events</a> for 
            <a href="{reverse('admin:shodan_student_changelist')}">students</a>."""
        return super().changelist_view(request, extra_context)


    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        else:
            dojo_ids = request.session.get('user_dojos', [])
            return queryset.filter(id__in=dojo_ids)

    def save_model(self, request, obj, form, change):
        """
            Make sure that user has permissions to the new dojo
            after creating it
        """
        super(DojoAdmin, self).save_model(request, obj, form, change)
        if not request.user.is_superuser and not change:
            dojo: Dojo = obj
            user: User = request.user
            # add the username to the user fk
            dojo.users.add(user)

            # add dojo to session
            dojo_ids = request.session.get('user_dojos', [])
            dojo_ids.append(dojo.id)
            session: SessionStore = request.session
            session['user_dojos'] = dojo_ids

    @admin.action(description='Unlock kiosk mode')
    def unlock_kiosk(self, request, queryset):
        updated = queryset.update(kiosk_locked=False, kiosk_failed_attempts=0)
        self.message_user(request, f'Kiosk unlocked for {updated} dojo(s).')


class AddressAdmin(DojoFkFilterModelAdmin):
    help_text = "Hello world"
    list_display = ('id', 'name', 'street', 'city', 'state')
    list_display_links = ('id', 'name')
    search_fields = ('id', 'name',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        # <a href="{reverse('admin:shodan_session_changelist')}">session</a>
        extra_context['documentation'] = \
            f"""<b>Help</b>: The address indicates the location of  
            <a href="{reverse('admin:shodan_session_changelist')}">sessions</a> and 
            <a href="{reverse('admin:dojoconf_event_changelist')}">events</a>."""
        return super().changelist_view(request, extra_context)

class ClassesAdmin(DojoFkFilterModelAdmin):
    list_display = ('id', 'name', 'address__name', 'time_from', 'time_to')
    list_display_links = ('id', 'name')
    search_fields = ('id', 'name',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        # <a href="{reverse('admin:shodan_session_changelist')}">session</a>
        extra_context['documentation'] = \
            f"""<b>Help</b>: A Karate Class template is used to create 
            <a href="{reverse('admin:shodan_session_changelist')}">sessions</a>, 
            which are defined by their type and skill level (e.g., Adults, Kids, Beginners), 
            frequency, 
            location (<a href="{reverse('admin:dojoconf_address_changelist')}">address</a>), 
            and duration."""
        return super().changelist_view(request, extra_context)


class EventAdmin(DojoFkFilterModelAdmin):
    list_display = ('id', 'name', 'requires_waiver')
    list_display_links = ('id', 'name')
    search_fields = ('id', 'name',)
    list_filter = ('requires_waiver',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        # <a href="{reverse('admin:shodan_session_changelist')}">session</a>
        extra_context['documentation'] = \
            f"""<b>Help</b>: Events supplement the regular training <a href="{reverse('admin:dojoconf_classes_changelist')}">classes</a>
             and are held occasionally 
            throughout the year (e.g., seminars and gradings). 
            An event may consist of one or multiple 
            <a href="{reverse('admin:shodan_session_changelist')}">sessions</a>."""
        return super().changelist_view(request, extra_context)

admin.site.register(Event, EventAdmin)
admin.site.register(Dojo, DojoAdmin)
admin.site.register(Address, AddressAdmin)
admin.site.register(Classes, ClassesAdmin)