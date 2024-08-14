from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import models
from djmoney.forms.fields import MoneyField

from shodan.models import Dojo, Event, Student


# Create your models here.
class Subscription(models.Model):
    FREQUENCY_CHOICES = [
        ('monthly', 'Monthly'),
        ('trimestral', 'Trimestral'),
        ('term', 'School Term'),
    ]
    dojo = models.ForeignKey(Dojo, on_delete=models.CASCADE)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    name = models.CharField(max_length=200, help_text='i.e "Adult, Children, Family"')
    frequency = models.CharField(max_length=200, help_text='i.e "Weekly"')
    price = MoneyField(max_digits=10, decimal_places=2, default_currency='AUD')
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

class Category(models.Model):
    dojo = models.ForeignKey(Dojo, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, help_text='i.e "Shimpads, Training material"')
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"[{self.id}] {self.name}"

    class Meta:
        verbose_name_plural = "Categories"

class Sale(models.Model):
    dojo = models.ForeignKey(Dojo, on_delete=models.CASCADE)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, blank=True, null=True, help_text='Subscription, Category or Event is required.')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, blank=True, null=True, help_text='Subscription, Category or Event is required.')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, blank=True, null=True, help_text='Subscription, Category or Event is required.')
    date = models.DateField()
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)
    cost = MoneyField(max_digits=10, decimal_places=2, default_currency='AUD')
    paid = MoneyField(max_digits=10, decimal_places=2, default_currency='AUD')
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def clean(self):
        if not self.subscription and not self.event and not self.category:
            raise ValidationError(
                {
                    'subscription': 'Subscription, Category or Event is required.',
                    'event': 'Subscription, Category or Event is required.',
                    'category': 'Subscription, Category or Event is required.',
                 }
            )

    def __str__(self):
        if self.subscription:
            return f"[{self.id}] {self.student} {self.paid}/{self.cost} {self.subscription__name} {self.date_from} {self.date_to} "
        elif self.event:
            return f"[{self.id}] {self.student} {self.paid}/{self.cost} {self.event__name} "
        elif self.category:
            return f"[{self.id}] {self.student} {self.paid}/{self.cost} {self.category__name} "
        else:
            return f"[{self.id}] {self.student} {self.paid}/{self.cost}"


class Expense(models.Model):
    dojo = models.ForeignKey(Dojo, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, blank=True, null=True, help_text='Optional, if related with an event.')
    name = models.CharField(max_length=200)
    date = models.DateField()
    cost = MoneyField(max_digits=10, decimal_places=2, default_currency='AUD')
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)