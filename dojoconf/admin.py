from django.contrib import admin
from django.forms import TimeField

from dojoconf.models import Dojo, Interval, Address, Classes


# Register your models here.
class DojoAdmin(admin.ModelAdmin):
    list_display = ('id', 'name',)
    list_display_links = ('id', 'name')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')


class StudentStatusAdmin(admin.ModelAdmin):
    list_display = ('id', 'name',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')

class IntervalAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'type', 'days_of_week', 'starting_at', 'finishing_at')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')

class AddressAdmin(admin.ModelAdmin):
    list_display = ('id', 'name',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')


class ClassesAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'address__name', 'time_from', 'time_to')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')

admin.site.register(Dojo, DojoAdmin)
admin.site.register(Interval, IntervalAdmin)
admin.site.register(Address, AddressAdmin)
admin.site.register(Classes, ClassesAdmin)