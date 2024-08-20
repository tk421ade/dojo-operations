from django.contrib import admin

from dojoconf.admin import DojoFkFilterModelAdmin
from .models import *

# Register your models here.

class SubscriptionCustomFrequencyInline(admin.StackedInline):
    model = SubscriptionCustomFrequency
    extra = 1  # Show one extra blank form

class SubscriptionProductAdmin(DojoFkFilterModelAdmin):
    list_display = ('id', 'name', 'frequency', 'amount', 'currency')
    inlines = [SubscriptionCustomFrequencyInline]
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')

class SubscriptionAdmin(DojoFkFilterModelAdmin):
    list_display = ('id', 'subscription_product__name', 'student__name', 'amount', 'currency', 'status')
    search_fields = ('id',  'subscription_product__name', 'student__name',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')


class SalesAdmin(DojoFkFilterModelAdmin):
    list_display = ('id', 'subscription__subscription_product__name','event__name', 'category__name', 'amount', 'paid')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')
    autocomplete_fields = ["dojo", "subscription", "category", "event", "student"]
    fieldsets = (
        ('General', {
            'fields': ('dojo',),
        }),
        ('Type of Sale', {
            'fields': ('subscription', 'category', 'event')
        }),
        ('Details', {
            'fields': ( 'date', 'student', 'amount', 'paid', 'currency',)
        }),
        ('Subscription Options', {
            'fields': ('date_from', 'date_to')
        }),
        ('Additional Fields', {
            'fields': ('notes', 'created_at', 'updated_at', 'deleted_at')
        }),
    )

class CategoryAdmin(DojoFkFilterModelAdmin):
    list_display = ('id', 'name',)
    search_fields = ('id', 'name',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')

class ExpenseAdmin(DojoFkFilterModelAdmin):
    list_display = ('id', 'name',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')


admin.site.register(SubscriptionProduct, SubscriptionProductAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Sale, SalesAdmin)
admin.site.register(Expense, ExpenseAdmin)