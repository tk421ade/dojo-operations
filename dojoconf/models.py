from datetime import datetime, timedelta

from django.contrib.auth.models import User
from timezone_field import TimeZoneField

from django.contrib.postgres.fields import ArrayField
from django.db import models


# Create your models here.
class Dojo(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(max_length=200)
    users = models.ManyToManyField(User, related_name='dojos')
    timezone =  TimeZoneField()
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"[{self.id}] {self.name}"


class Interval(models.Model):
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
    name = models.CharField(max_length=200, help_text='i.e "Every Monday"')
    type = models.CharField(max_length=9, help_text='i.e "Weekly"', choices=TYPES)
    days_of_week = ArrayField(models.CharField(max_length=9, choices=DAY_OF_WEEK_CHOICES),
                              help_text='i.e "monday,tuesday". Accepted values: monday,tuesday,wednesday,thursday,friday,saturday,sunday"')
    starting_at = models.DateField()
    finishing_at = models.DateField(null=True, blank=True, help_text='The maximum value and the default is one year.')
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"[{self.id}] {self.name}"

    class Meta:
        verbose_name = "Class Interval"
        verbose_name_plural = "Class Intervals"

class Address(models.Model):
    dojo = models.ForeignKey(Dojo, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, help_text='Friendly name')
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=20, decimal_places=15, null=True, blank=True)
    longitude = models.DecimalField(max_digits=20, decimal_places=15, null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"[{self.id}] {self.name}"

class Classes(models.Model):
    dojo = models.ForeignKey(Dojo, on_delete=models.CASCADE)
    interval = models.ForeignKey(Interval, on_delete=models.CASCADE)
    address = models.ForeignKey(Address, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, help_text='i.e "Adults"')
    time_from = models.TimeField(help_text='i.e "Starting Local Time"')
    time_to = models.TimeField(help_text='i.e "Finishing Local Time"')
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def get_duration(self):
        return timedelta(hours=self.time_to.hour - self.time_from.hour, minutes=self.time_to.minute - self.time_from.minute)

    def get_minutes(self):
        time_diff = self.get_duration()
        return time_diff.total_seconds() / 60

    def __str__(self):
        return f"[{self.id}] {self.name}"