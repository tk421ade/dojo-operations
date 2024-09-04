import logging
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.urls import reverse
from django.utils.safestring import mark_safe

from financial.models import Sale, MembershipProduct, Membership
from shodan.models import Student


def autocreate_sales_from_memberships_for_dojo(request, dojo_id):

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
                    date_to += __add_quarter(date_from)
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

    return active_students.count(), membership_product_count, membership_count



def __add_quarter(self, date_field):
    month = date_field.month + 3
    year = date_field.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    day = min(date_field.day, [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return date(year, month, day)