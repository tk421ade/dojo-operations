from django.contrib import admin
from .models import *

# Register your models here.
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')

class SalesAdmin(admin.ModelAdmin):
    list_display = ('id', 'subscription__name','event__name', 'category__name', 'cost', 'paid')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')

class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('id', 'name',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')


admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Sale, SalesAdmin)
admin.site.register(Expense, ExpenseAdmin)