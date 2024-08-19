from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import models

from dojoconf.models import Dojo, Interval, Address, Classes, Event


class Student(models.Model):
    STATUS = [
        ('active', 'ACTIVE'),
        ('inactive', 'INACTIVE'),
    ]
    dojo = models.ForeignKey(Dojo, on_delete=models.CASCADE)
    status = models.CharField(max_length=9, choices=STATUS)
    name = models.CharField(max_length=200)
    email = models.EmailField(max_length=200)
    kyu = models.IntegerField(null=True, blank=True)
    dan = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"[{self.id}] {self.name}"


class Session(models.Model):
    dojo = models.ForeignKey(Dojo, on_delete=models.CASCADE)
    classes = models.ForeignKey(Classes, on_delete=models.CASCADE, blank=True, null=True, help_text='Event or Classes needs to be defined')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, blank=True, null=True, help_text='Event or Classes needs to be defined')
    date = models.DateField()
    name = models.CharField(max_length=200, blank=True, null=True, help_text='Optional. Autogenerated if empty. i.e "Adults Monday Session" or "Oct 2024 Seminar"')
    time_from = models.TimeField(null=True, blank=True,help_text='For standard classes will be calculated automatically if empty')
    time_to = models.TimeField(null=True, blank=True,help_text='For standard classes will be calculated automatically if empty')
    duration = models.DurationField(null=True, blank=True, help_text='For standard classes will be calculated automatically if empty')
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def get_duration(self):
        if self.time_to and self.time_from:
            return timedelta(hours=self.time_to.hour - self.time_from.hour, minutes=self.time_to.minute - self.time_from.minute)


    def get_minutes(self):
        time_diff = self.get_duration()
        if time_diff:
            return time_diff.total_seconds() / 60

    def save(self, *args, **kwargs):

        if self.classes and not self.time_from:
            self.time_from = self.classes.time_from

        if self.classes and not self.time_to:
            self.time_to = self.classes.time_to

        if self.classes and not self.duration:
            self.duration = self.classes.get_duration()

        if not self.name:
            if self.event:
                self.name = f'Event {self.event.name}'
            elif self.classes:
                self.name = f'{self.classes.name } class at {self.date} from {self.time_from} to {self.time_to} ({self.get_minutes()} minutes)'
            else:
                self.name = f'Session at {self.date}'

        super().save(*args, **kwargs)

    def clean(self):
        if not self.classes and not self.event:
            raise ValidationError(
                {'classes': 'You need to define a classes or a event.',
                 'event': 'You need to define a classes or a event.'})

    def __str__(self):
        return f"[{self.id}] {self.name}"

class Attendance(models.Model):
    dojo = models.ForeignKey(Dojo, on_delete=models.CASCADE)
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField(null=True, blank=True, help_text='It will be populated automatically if empty')
    duration = models.DurationField(null=True, blank=True, help_text='Optional, it will be calculated automatically if empty (i.e 1:30 for 90 minutes)')
    points = models.IntegerField(null=True, blank=True, help_text='Optional, if it adds points towards the next grading.')
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.duration:
            self.duration = self.session.duration
        if not self.date:
            self.date = self.session.date

        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.id}] {self.student.name} for {self.session.name}"