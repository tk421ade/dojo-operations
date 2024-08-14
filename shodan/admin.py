from django.contrib import admin
from django.forms import TimeField

from .models import *


class StudentAdmin(admin.ModelAdmin):
    list_display = ('id', 'dojo__name', 'name', 'status', 'kyu', 'dan')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')
    list_display_links = ('id', 'name')

class EventAdmin(admin.ModelAdmin):
    list_display = ('id', 'name',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')

class SessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')

class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('id', 'student__name','session__name',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')


# Admin-editable models

admin.site.register(Student, StudentAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Session, SessionAdmin)
admin.site.register(Attendance, AttendanceAdmin)


# Restricted models
#admin.site.register(StudentStatus, StudentStatusAdmin)
