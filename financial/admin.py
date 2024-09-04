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

class membershipCustomFrequencyInline(admin.StackedInline):
    model = MembershipCustomFrequency
    extra = 1  # Show one extra blank form

class membershipProductAdmin(DojoFkFilterModelAdmin):
    list_display = ('id', 'name', 'frequency', 'amount', 'currency')
    list_display_links = ('id', 'name')
    search_fields = ('id', 'name',)
    #inlines = [membershipCustomFrequencyInline]
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        # <a href="{reverse('admin:shodan_student_changelist')}">students</a>
        extra_context['documentation'] = \
            f"""<b>Help</b>: 
            Membership Products specify the pricing and payment schedule for 
            <a href="{reverse('admin:shodan_student_changelist')}">students</a> 
            to <a href="{reverse('admin:financial_sale_changelist')}">subscribe</a> 
            and attend <a href="{reverse('admin:shodan_session_changelist')}">sessions</a>."""
        return super().changelist_view(request, extra_context)

class MembershipAdmin(DojoFkFilterModelAdmin):
    list_display = ('id',  'student__name', 'membership_product__name', 'amount', 'currency', 'status')
    list_display_links = ('id', 'student__name')
    search_fields = ('id',  'membership_product__name', 'student__name',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        # <a href="{reverse('admin:shodan_student_changelist')}">students</a>
        extra_context['documentation'] = \
            f"""<b>Help</b>: 
            Membership formalizes a student's commitment to regular karate training at the dojo, 
            as defined by the <a href="{reverse('admin:financial_membershipproduct_changelist')}">Membership Product</a>, 
            and establishes a recurring payment arrangement that generates 
            <a href="{reverse('admin:financial_sale_changelist')}">sales</a>. 
            """
        return super().changelist_view(request, extra_context)


class SaleAdmin(DojoFkFilterModelAdmin):
    change_list_template = 'admin/financial/sale/change_list.html'
    list_display = ('id', 'student__name', 'date_from', 'date_to', 'membership__membership_product__name','event__name', 'category__name', 'amount', 'paid', 'created_at_tz')
    list_display_links = ('id', 'student__name',)
    search_fields = ('id','student__name', 'membership__membership_product__name','event__name', 'category__name',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')
    autocomplete_fields = ["dojo", "membership", "category", "event", "student"]
    fieldsets = (
        ('General', {
            'fields': ('dojo',),
        }),
        ('Type of Sale', {
            'fields': ('membership', 'category', 'event')
        }),
        ('Details', {
            'fields': ( 'date', 'student', 'amount', 'paid', 'currency',)
        }),
        ('membership Options', {
            'fields': ('date_from', 'date_to')
        }),
        ('Additional Fields', {
            'fields': ('notes', 'created_at', 'updated_at', 'deleted_at')
        }),
    )
    date_hierarchy = "date"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        # <a href="{reverse('admin:shodan_student_changelist')}">students</a>

        attendance_doc = "."
        if request.session.has_key('dojo_id'):
            dojo_id = request.session.get('dojo_id')
            dojo = Dojo.objects.get(id=dojo_id)
            attendance_doc = f" via <a href='https://{dojo.hostname}'>{dojo.hostname}</a>."

        extra_context['documentation'] = \
            f"""<b>Help</b>: Sales track income from student <a href="{reverse('admin:financial_membership_changelist')}">memberships</a> 
            and other session-related items. 
            You can automatically update sales from memberships by clicking the 
            'Update Sales From Memberships' button. 
            Additionally, <a href="{reverse('admin:shodan_student_changelist')}">students</a> 
            will receive expiration reminders when registering 
            <a href="{reverse('admin:shodan_attendance_changelist')}">attendance</a> {attendance_doc}.
            """
        return super().changelist_view(request, extra_context)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('membership/', self.admin_site.admin_view(self.membership), name='financial_sale_membership'),
        ]
        return custom_urls + urls

    def membership(self, request):
        """
            Add all pending memberships
        """
        dojo_id = request.session.get('dojo_id')

        # find students
        active_students = Student.objects.filter(dojo_id=dojo_id, status='active')
        logging.warning(f"Active Students {len(active_students)}")

        current_date = date.today()

        # do the students has active memberships ?
        for student in active_students:
            sale = Sale.objects.filter(
                dojo_id=dojo_id,
                student_id=student.id,
                date_from__lte=current_date,
                date_to__gte=current_date,
                membership__isnull=False
            ).first()
            if sale:
                logging.warning(f"Active Student {student.name} has a sale {sale.id} ({sale.paid} / {sale.amount}) "
                                f"from ${sale.date_from} to ${sale.date_to}")
            else:
                logging.warning(f"Active Student {student.name} requires to create a sale")

                membership: Membership = Membership.objects.filter(
                    dojo_id=dojo_id,
                    student_id=student.id,
                    status='active',
                ).first()

                if not membership:
                    messages.warning(request, f"Active Student '{student.name}' does not have an active membership")
                    logging.warning(f"Active Student '{student.name}' does not have an active membership")
                else:

                    # find the latest sale
                    latest_sale = Sale.objects.filter(student_id=student.id).order_by('-date_to').last()

                    if latest_sale and latest_sale.date_to:
                        #date_from = (latest_sale.date_to + timedelta(days=1)).date()
                        date_from = (latest_sale.date_to + timedelta(days=1))
                    else:
                        date_from = date.today()

                    # calculate date_from and date_to
                    date_to = date_from
                    membership_frequency = membership.membership_product.frequency
                    if membership_frequency == MembershipProduct.MONTHLY:
                        date_to += relativedelta(months=1)
                    elif membership_frequency == MembershipProduct.QUARTERLY:
                        date_to += self.__add_quarter(date_from)
                    else:
                        date_to = None
                        error_message = f"membership Product Frequency '{membership_frequency}'"
                        f" has not been implemented. Please update 'Date To' manually "
                        f"for the sale created to student '{student.name}'"
                        messages.error(request, error_message)
                        logging.error(error_message)

                    sale = Sale.objects.create(
                        dojo_id=dojo_id,
                        student_id=student.id,
                        membership_id=membership.id,
                        amount=membership.amount,
                        paid=0,
                        currency=membership.currency,
                        date_from=date_from,
                        date_to=date_to,
                        date=current_date,
                    )
                    url = reverse('admin:financial_sale_change', args=(sale.id,))
                    messages.success(request, mark_safe(f"Created an <a href='{url}'>unpaid sale</a> for active student '{student.name}'"))

        membership_count = Sale.objects.filter(dojo_id=dojo_id).count()
        membership_product_count = MembershipProduct.objects.filter(dojo_id=dojo_id).count()

        messages.success(request, f"{active_students.count()} Student(s), {membership_count} membership(s) in {membership_product_count} membership Product(s) processed.")

        # check whether the memberships are correctly configured\
        # do we have memberships ?
        if not membership_count:
            messages.warning(request, f"Have you configured memberships?")

        if not membership_product_count:
            messages.warning(request, f"Have you configured Products for memberships ?")


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
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        # <a href="{reverse('admin:shodan_student_changelist')}">students</a>
        extra_context['documentation'] = \
            f"""<b>Help</b>: 
            Categories are used to classify and organize 
            <a href="{reverse('admin:financial_sale_changelist')}">sales</a> 
            and <a href="{reverse('admin:financial_expense_changelist')}">expenses</a> 
            (e.g., Shinpads, Training Materials, etc.)."""
        return super().changelist_view(request, extra_context)

class ExpenseAdmin(DojoFkFilterModelAdmin):
    list_display = ('id', 'name', 'category__name', 'event__name', 'amount', 'currency')
    search_fields = ('id', 'name',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        # <a href="{reverse('admin:shodan_student_changelist')}">students</a>
        extra_context['documentation'] = \
            f"""<b>Help</b>: Expenses track the costs associated with running 
            <a href="{reverse('admin:shodan_session_changelist')}">sessions</a>."""
        return super().changelist_view(request, extra_context)

admin.site.register(MembershipProduct, membershipProductAdmin)
admin.site.register(Membership, MembershipAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Sale, SaleAdmin)
admin.site.register(Expense, ExpenseAdmin)