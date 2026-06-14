import os
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.storage import FileSystemStorage
from django.urls import reverse
from django.utils.timezone import now as tz_now
from django.utils.safestring import mark_safe
from timezone_field import TimeZoneField

from django.contrib.postgres.fields import ArrayField
from django.db import models

try:
    from storages.backends.s3boto3 import S3Boto3Storage
except ImportError:
    S3Boto3Storage = None


def get_file_storage():
    if all([
        getattr(settings, 'AWS_ACCESS_KEY_ID', None),
        getattr(settings, 'AWS_SECRET_ACCESS_KEY', None),
        getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None),
        getattr(settings, 'AWS_S3_REGION_NAME', None),
    ]) and S3Boto3Storage:
        return S3Boto3Storage()
    return FileSystemStorage(location=settings.BASE_DIR / 'media')


def _create_dojo_logo_path(instance, filename):
    dojo_id = instance.id or 'new'
    return os.path.join(
        str(f"dojo_{dojo_id}"),
        f"logo_{filename}",
    )


# Create your models here.
class Dojo(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(max_length=200)
    users = models.ManyToManyField(User, related_name='dojos')
    timezone =  TimeZoneField()
    hostname = models.CharField(null=True, blank=True, max_length=255, help_text='Hosted hostname (i.e dojo.brightonkarate.com.au)')
    kiosk_pin = models.CharField(max_length=6, null=True, blank=True, help_text='4-6 digit PIN for activating Kiosk Mode on the student-facing landing page.')
    kiosk_locked = models.BooleanField(default=False, help_text='When True, all kiosk PIN entry is blocked. Admin must unlock.')
    kiosk_failed_attempts = models.IntegerField(default=0, help_text='Consecutive failed kiosk PIN attempts. Resets on success or admin unlock.')
    logo = models.FileField(upload_to=_create_dojo_logo_path, storage=get_file_storage, null=True, blank=True, help_text='Dojo logo (transparent PNG designed for white background). Displayed on all public pages.')
    created_at = models.DateTimeField(default=tz_now)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"[{self.id}] {self.name}"

class Address(models.Model):
    dojo = models.ForeignKey(Dojo, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, help_text='Friendly name')
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=20, decimal_places=15, null=True, blank=True,
                                   help_text=mark_safe("<a target='_blank' href='https://www.latlong.net/'>Find Latitude</a>"))
    longitude = models.DecimalField(max_digits=20, decimal_places=15, null=True, blank=True,
                                    help_text=mark_safe("<a target='_blank' href='https://www.latlong.net/'>Find Longitude</a>"))
    created_at = models.DateTimeField(default=tz_now)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"[{self.id}] {self.name}"

class Classes(models.Model):
    TYPES = [
        ('weekly', 'Weekly'),
    ]
    DAY_OF_WEEK_CHOICES = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    dojo = models.ForeignKey(Dojo, on_delete=models.CASCADE)
    address = models.ForeignKey(Address, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, help_text='i.e "Adults"')
    type = models.CharField(max_length=9, help_text='i.e "Weekly"', choices=TYPES)
    days_of_week = ArrayField(models.CharField(max_length=9, choices=DAY_OF_WEEK_CHOICES),
                              help_text='i.e "monday,tuesday". Accepted values: monday,tuesday,wednesday,thursday,friday,saturday,sunday"')
    starting_at = models.DateField()
    finishing_at = models.DateField(null=True, blank=True, help_text='The maximum value and the default is one year.')
    time_from = models.TimeField(help_text='i.e "Starting Local Time"')
    time_to = models.TimeField(help_text='i.e "Finishing Local Time"')
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=tz_now)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def get_duration(self):
        return timedelta(hours=self.time_to.hour - self.time_from.hour, minutes=self.time_to.minute - self.time_from.minute)

    def get_minutes(self):
        time_diff = self.get_duration()
        return time_diff.total_seconds() / 60

    def __str__(self):
        return f"[{self.id}] {self.name}"


class Event(models.Model):
    dojo = models.ForeignKey(Dojo, on_delete=models.CASCADE)
    address = models.ForeignKey(Address, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, help_text='i.e "Seminar, Grading, Competition, etc."')
    notes = models.TextField(null=True, blank=True)
    requires_waiver = models.BooleanField(default=False, help_text='If enabled, an "Events" button appears on the landing page linking to the waiver form.')
    waiver_success_message = models.TextField(null=True, blank=True, help_text='Custom message shown on the waiver success page after submission. Leave blank for default message.')
    created_at = models.DateTimeField(default=tz_now)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"[{self.id}] {self.name}"