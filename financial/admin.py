import logging
from datetime import date
from django.contrib import admin, messages
from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, reverse
from django.shortcuts import redirect
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
    change_list_template = 'admin/financial/sale/change_list.html'
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
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('subscription/', self.admin_site.admin_view(self.subscription), name='financial_sale_subscription'),
        ]
        return custom_urls + urls

    def subscription(self, request):
        dojo_id = request.session.get('dojo_id')

        # find students
        active_students = Student.objects.filter(dojo_id=dojo_id, status='active')
        logging.warning(f"Active Students {len(active_students)}")

        current_date = date.today()

        # do the students has active subscriptions ?
        for student in active_students:
            sale = Sale.objects.filter(
                dojo_id=dojo_id,
                student_id=student.id,
                date_from__lte=current_date,
                date_to__gte=current_date,
                subscription__isnull=False
            ).first()
            if sale:
                logging.warning(f"Active Student {student.name} has a sale {sale.id} ({sale.paid} / {sale.amount}) "
                                f"from ${sale.date_from} to ${sale.date_to}")
            else:
                logging.warning(f"Active Student {student.name} requires to create a sale")

                subscription = Subscription.objects.filter(
                    dojo_id=dojo_id,
                    student_id=student.id,
                    status='active',
                ).first()

                if not subscription:
                    messages.warning(request, f"Active Student '{student.name}' does not have an active subscription")
                    logging.warning(f"Active Student '{student.name}' does not have an active subscription")
                else:
                    messages.success(request, f"Created an unpaid sale for active student '{student.name}'")
                    # TODO add date_from and date_to
                    Sale.objects.create(
                        dojo_id=dojo_id,
                        student_id=student.id,
                        subscription_id=subscription.id,
                        amount=subscription.amount,
                        paid=0,
                        currency=subscription.currency,
                        date=current_date,
                    )
        #return HttpResponse("Hello, World!")
        return redirect(reverse('admin:financial_sale_changelist'))


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