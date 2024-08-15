from django.contrib import admin
from django.forms import TimeField

from dojoconf.admin import DojoFkFilterModelAdmin
from .forms import AdminSessionForm
from .models import *


class StudentAdmin(DojoFkFilterModelAdmin):
    list_display = ('id', 'dojo__name', 'name', 'status', 'kyu', 'dan')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')
    list_display_links = ('id', 'name')
    list_filter = ('status',)
    search_fields = ('name',)

class EventAdmin(DojoFkFilterModelAdmin):
    list_display = ('id', 'name',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')
    list_filter = ('date',)

class SessionAdmin(DojoFkFilterModelAdmin):
    list_display = ('id', 'name')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')
    list_filter = ('date',)
    form = AdminSessionForm

class AttendanceAdmin(DojoFkFilterModelAdmin):
    list_display = ('id', 'date', 'student__name','session__name', 'duration', 'points')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')
    search_fields = ('student__name', 'session__name')
    list_filter = ('date',)


# Admin-editable models

admin.site.register(Student, StudentAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Session, SessionAdmin)
admin.site.register(Attendance, AttendanceAdmin)


# Restricted models
#admin.site.register(StudentStatus, StudentStatusAdmin)
