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
from .service import autocreate_sales_from_memberships_for_dojo


# Register your models here.

class membershipCustomFrequencyInline(admin.StackedInline):
    model = MembershipCustomFrequency
    extra = 1  # Show one extra blank form

class membershipProductAdmin(DojoFkFilterModelAdmin):
    list_display = ('id', 'name', 'frequency', 'amount', 'currency')
    list_display_links = ('id', 'name')
    search_fields = ('id', 'name',)
    inlines = [membershipCustomFrequencyInline]
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
            if dojo_id:
                dojo = Dojo.objects.get(id=dojo_id)
                attendance_doc = f" via <a href='https://{dojo.hostname}'>{dojo.hostname}</a>."

            # TODO multidojo support
            #dojos = Dojo.objects.filter(users__username=request.user.username)
            # attendance_doc = f"."
            # for i, dojo in enumerate(dojos):
            #     if i == 0:
            #         attendance_doc = f"via "
            #
            #     if not (i == 0 or i == len(dojos) - 1):  # not the first of the last
            #         attendance_doc += ", "
            #
            #     attendance_doc += f"<a href='https://{dojo.hostname}'>{dojo.hostname}</a>"
            #
            #     if i == len(dojos) - 1:
            #         attendance_doc += "."



        extra_context['documentation'] = \
            f"""<b>Help</b>: Sales track income from student <a href="{reverse('admin:financial_membership_changelist')}">memberships</a> 
            and other session-related items. 
            You can automatically update sales from memberships by clicking the 
            'Update Sales From Memberships' button. 
            Additionally, <a href="{reverse('admin:shodan_student_changelist')}">students</a> 
            will receive expiration reminders when registering 
            <a href="{reverse('admin:shodan_attendance_changelist')}">attendance</a> {attendance_doc}
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
        dojos = Dojo.objects.filter(users__username=request.user.username)
        active_students_count = 0
        membership_product_count = 0
        membership_count = 0
        for dojo in dojos:
            dojo_active_students_count, dojo_membership_product_count, dojo_membership_count = autocreate_sales_from_memberships_for_dojo(request, dojo.pk)
            active_students_count += dojo_active_students_count
            membership_product_count += dojo_membership_product_count
            membership_count += dojo_membership_count

        messages.success(request, f"{active_students_count} Student(s), {membership_count} membership(s) in {membership_product_count} membership Product(s) processed.")

        # check whether the memberships are correctly configured
        if not active_students_count:
            messages.warning(request, f"Do you have active students ?")

        if not membership_count:
            messages.warning(request, f"Have you configured memberships?")

        if not membership_product_count:
            messages.warning(request, f"Have you configured Products for memberships ?")

        #return HttpResponse("Hello, World!")
        return redirect(reverse('admin:financial_sale_changelist'))




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