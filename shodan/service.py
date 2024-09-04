import logging
from datetime import datetime, timedelta, date

from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.urls import reverse
from django.utils.safestring import mark_safe

from dojoconf.models import Classes
from financial.models import Sale, Membership, MembershipProduct
from shodan.models import Session, Student


def autocreate_sessions_for_dojo(request, dojo_id):

    weekday_mapping = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6
    }

    all_classes = Classes.objects.filter(dojo_id=dojo_id)
    for classes in all_classes:
        current_date = classes.interval.starting_at
        if current_date < datetime.now().date():
            current_date = datetime.now().date()
        finishing_date = datetime.now().date() + relativedelta(months=1)
        if classes.interval.finishing_at and finishing_date > classes.interval.finishing_at:
            finishing_date = classes.interval.finishing_at

        logging.warning(f"Calculating all working days from {current_date} to {finishing_date}")
        days_of_week = classes.interval.days_of_week
        already_exists_count = 0
        new_count = 0
        while current_date <= finishing_date:
            for day in days_of_week:
                if day in weekday_mapping:
                    if current_date.weekday() == weekday_mapping[day]:
                        logging.warning(f"Creating Session")

                        # check if the session already exists
                        sessions = Session.objects.filter(
                            date=current_date,
                            dojo_id=classes.dojo.pk,
                            classes_id=classes.pk
                        )
                        if sessions.exists():
                            already_exists_count += 1
                        else:
                            new_count += 1
                            Session.objects.create(
                                dojo_id=classes.dojo.pk,
                                classes_id=classes.pk,
                                date=current_date,
                            )
                else:
                    logging.warning(f"{day} not found at interval {classes.interval}")

            current_date += timedelta(days=1)

        if new_count:
            messages.success(request, f"Processing Classes {classes.name}: {new_count} sessions created from {current_date} to {finishing_date}")
        if already_exists_count:
            messages.success(request, f"Processing Classes {classes.name}: {already_exists_count} sessions already existed from {current_date} to {finishing_date}")

        return len(all_classes)

