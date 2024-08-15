from django.contrib import admin
from django.forms import TimeField

from dojoconf.models import Dojo, Interval, Address, Classes

class DojoFkFilterModelAdmin(admin.ModelAdmin):
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'dojo':
            if not request.user.is_superuser:
                dojo_ids = request.session.get('user_dojos', [])
                kwargs['queryset'] = Dojo.objects.filter(id__in=dojo_ids)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        if not request.user.is_superuser:
            dojo_ids = request.session.get('user_dojos', [])
            initial['dojo'] = dojo_ids[0]
        return initial

# Register your models here.
class DojoAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'timezone')
    list_display_links = ('id', 'name')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        else:
            dojo_ids = request.session.get('user_dojos', [])
            return queryset.filter(id__in=dojo_ids)

class StudentStatusAdmin(DojoFkFilterModelAdmin):
    list_display = ('id', 'name',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')

class IntervalAdmin(DojoFkFilterModelAdmin):
    list_display = ('id', 'name', 'type', 'days_of_week', 'starting_at', 'finishing_at')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')

class AddressAdmin(DojoFkFilterModelAdmin):
    list_display = ('id', 'name',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')



class ClassesAdmin(DojoFkFilterModelAdmin):
    list_display = ('id', 'name', 'address__name', 'interval__name', 'time_from', 'time_to')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')

admin.site.register(Dojo, DojoAdmin)
admin.site.register(Interval, IntervalAdmin)
admin.site.register(Address, AddressAdmin)
admin.site.register(Classes, ClassesAdmin)