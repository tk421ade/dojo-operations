import logging
from datetime import date, timedelta
from typing import Any

from dateutil.relativedelta import relativedelta
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
    list_display_links = ('id', 'name')
    search_fields = ('id', 'name',)
    inlines = [SubscriptionCustomFrequencyInline]
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')

class SubscriptionAdmin(DojoFkFilterModelAdmin):
    list_display = ('id', 'subscription_product__name', 'student__name', 'amount', 'currency', 'status')
    list_display_links = ('id', 'subscription_product__name')
    search_fields = ('id',  'subscription_product__name', 'student__name',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')


class SaleAdmin(DojoFkFilterModelAdmin):
    change_list_template = 'admin/financial/sale/change_list.html'
    list_display = ('id', 'student__name', 'date_from', 'date_to', 'subscription__subscription_product__name','event__name', 'category__name', 'amount', 'paid', 'created_at_tz')
    list_display_links = ('id', 'student__name',)
    search_fields = ('id','student__name', 'subscription__subscription_product__name','event__name', 'category__name',)
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
        """
            Add all pending subscriptions
        """
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

                subscription: Subscription = Subscription.objects.filter(
                    dojo_id=dojo_id,
                    student_id=student.id,
                    status='active',
                ).first()

                if not subscription:
                    messages.warning(request, f"Active Student '{student.name}' does not have an active subscription")
                    logging.warning(f"Active Student '{student.name}' does not have an active subscription")
                else:

                    # find the latest sale
                    latest_sale = Sale.objects.filter(student_id=student.id).order_by('-date_to').last()

                    if latest_sale and latest_sale.date_to:
                        date_from = (latest_sale.date_to + timedelta(days=1)).date()
                    else:
                        date_from = date.today()

                    # calculate date_from and date_to
                    date_to = date_from
                    subscription_frequency = subscription.subscription_product.frequency
                    if subscription_frequency == SubscriptionProduct.MONTHLY:
                        date_to += relativedelta(months=1)
                    elif subscription_frequency == SubscriptionProduct.QUARTERLY:
                        date_to += self.__add_quarter(date_from)
                    else:
                        date_to = None
                        error_message = f"Subscription Product Frequency '{subscription_frequency}'"
                        f" has not been implemented. Please update 'Date To' manually "
                        f"for the sale created to student '{student.name}'"
                        messages.error(request, error_message)
                        logging.error(error_message)

                    sale = Sale.objects.create(
                        dojo_id=dojo_id,
                        student_id=student.id,
                        subscription_id=subscription.id,
                        amount=subscription.amount,
                        paid=0,
                        currency=subscription.currency,
                        date_from=date_from,
                        date_to=date_to,
                        date=current_date,
                    )
                    url = reverse('admin:financial_sale_change', args=(sale.id,))
                    messages.success(request, mark_safe(f"Created an <a href='{url}'>unpaid sale</a> for active student '{student.name}'"))

        subscription_count = Sale.objects.filter(dojo_id=dojo_id).count()
        subscription_product_count = SubscriptionProduct.objects.filter(dojo_id=dojo_id).count()

        messages.success(request, f"{active_students.count()} Student(s), {subscription_count} Subscription(s) in {subscription_product_count} Subscription Product(s) processed.")

        # check whether the subscriptions are correctly configured\
        # do we have subscriptions ?
        if not subscription_count:
            messages.warning(request, f"Have you configured Subscriptions?")

        if not subscription_product_count:
            messages.warning(request, f"Have you configured Products for Subscriptions ?")


        #return HttpResponse("Hello, World!")
        return redirect(reverse('admin:financial_sale_changelist'))

    def __add_quarter(self, date_field):
        month = date_field.month + 3
        year = date_field.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        day = min(date_field.day, [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
        return date(year, month, day)


class CategoryAdmin(DojoFkFilterModelAdmin):
    list_display = ('id', 'name',)
    search_fields = ('id', 'name',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')

class ExpenseAdmin(DojoFkFilterModelAdmin):
    list_display = ('id', 'name', 'category__name', 'event__name', 'amount', 'currency')
    search_fields = ('id', 'name',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')


admin.site.register(SubscriptionProduct, SubscriptionProductAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Sale, SaleAdmin)
admin.site.register(Expense, ExpenseAdmin)