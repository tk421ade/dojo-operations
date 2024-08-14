from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import models

from dojoconf.models import Dojo, StudentStatus, Interval, Address, Classes


class Student(models.Model):
    dojo = models.ForeignKey(Dojo, on_delete=models.CASCADE)
    status = models.ForeignKey(StudentStatus, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    email = models.EmailField(max_length=200)
    kyu = models.IntegerField(null=True, blank=True)
    dan = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"[{self.id}] {self.name}"







class Event(models.Model):
    dojo = models.ForeignKey(Dojo, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, help_text='i.e "Adults"')
    address = models.ForeignKey(Address, on_delete=models.CASCADE)
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"[{self.id}] {self.name}"


class Session(models.Model):
    dojo = models.ForeignKey(Dojo, on_delete=models.CASCADE)
    classes = models.ForeignKey(Classes, on_delete=models.CASCADE, blank=True, null=True, help_text='Event or Classes needs to be defined')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, blank=True, null=True, help_text='Event or Classes needs to be defined')
    name = models.CharField(max_length=200, help_text='i.e "Adults Monday Session" or "Oct 2024 Seminar"')
    date = models.DateField()
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    def clean(self):
        if not self.classes and not self.event:
            raise ValidationError(
                {'classes': 'You need to define a classes or a event.',
                 'event': 'You need to define a classes or a event.'})

class Attendance(models.Model):
    dojo = models.ForeignKey(Dojo, on_delete=models.CASCADE)
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    minutes = models.IntegerField(null=True, blank=True)
    points = models.IntegerField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)


    def __str__(self):
        return f"[{self.id}] {self.student__name} {self.session__name}"