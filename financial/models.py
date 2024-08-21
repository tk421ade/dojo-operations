from datetime import datetime, timezone
from email.policy import default

from django.utils.safestring import mark_safe
from django.core.exceptions import ValidationError
from django.db import models
from djmoney.forms.fields import MoneyField

from shodan.models import Dojo, Event, Student

CURRENCIES = [('AUD', 'AUD'),]

# Create your models here.
class SubscriptionProduct(models.Model):
    MONTHLY = 'monthly'
    QUARTERLY = 'quarterly'
    CUSTOM = 'custom'
    FREQUENCY_CHOICES = [
        (MONTHLY, 'Monthly'),
        (QUARTERLY, 'Quarterly'),
        (CUSTOM, 'Custom'),
    ]
    dojo = models.ForeignKey(Dojo, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, help_text='i.e "Adult, Children, Family"')
    frequency = models.CharField(max_length=200, choices=FREQUENCY_CHOICES, help_text='i.e "Monthly, Quarterly, Custom (i.e School Term)"')
    #price = MoneyField(max_digits=10, decimal_places=2, default_currency='AUD')
    amount = models.DecimalField(max_digits=6, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CURRENCIES, default='AUD')
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"[{self.id}] {self.name}"

class SubscriptionCustomFrequency(models.Model):
    dojo = models.ForeignKey(Dojo, on_delete=models.CASCADE)
    frequency = models.TextField(help_text=mark_safe("""
    Each row is a date. You can add ranges (i.e '2024-08-01 to 2024-08-30' or single days (i.e 2024-08-01))<br>
    <br>
    For example, to create a subscription that will cover 4 payments, one per school holidays in 2024 in SA, 
    those will be the contents:<br>
    2024-01-29 to 2024-04-12<br>
    2024-04-29 to 2024-07-05<br>
    2024-07-22 to 2024-09-27<br>
    2024-10-14 to 2024-12-13<br>
    """))
    subscription_product = models.OneToOneField(SubscriptionProduct, on_delete=models.CASCADE, null=True)


class Subscription(models.Model):
    STATUS = [
        ('active', 'ACTIVE'),
        ('cancelled', 'CANCELLED'),
    ]
    dojo = models.ForeignKey(Dojo, on_delete=models.CASCADE)
    subscription_product = models.ForeignKey(SubscriptionProduct, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS, default='active')
    amount = models.DecimalField(max_digits=6, decimal_places=2, help_text="Auto populated if empty", null=True, blank=True)
    currency = models.CharField(max_length=3, choices=CURRENCIES, default='AUD')
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.amount and self.subscription_product:
            self.amount = self.subscription_product.amount
        if not self.currency and self.subscription_product:
            self.currency = self.subscription_product.currency

        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.id}] {self.subscription_product.name} {self.student.name}"


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
    date_from = models.DateField(null=True, blank=True, help_text="Auto populated if type is subscription and it is empty")
    date_to = models.DateField(null=True, blank=True, help_text="Auto populated if type is subscription and it is empty")
    #cost = MoneyField(max_digits=10, decimal_places=2, default_currency='AUD')
    amount = models.DecimalField(max_digits=6, decimal_places=2, help_text="Auto populated if empty")
    paid = models.DecimalField(max_digits=6, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CURRENCIES, default='AUD')
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
            return f"[{self.id}] {self.student} {self.paid}/{self.amount}  {self.subscription.subscription_product.name} {self.date_from} {self.date_to} "
        elif self.event:
            return f"[{self.id}] {self.student} {self.paid}/{self.amount} {self.event__name} "
        elif self.category:
            return f"[{self.id}] {self.student} {self.paid}/{self.amount} {self.category__name} "
        else:
            return f"[{self.id}] {self.student} {self.paid}/{self.amount}"


class Expense(models.Model):
    dojo = models.ForeignKey(Dojo, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, blank=True, null=True, help_text='Optional, if related with an event.')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, blank=True, null=True, help_text='Optional, if related with a category.')
    name = models.CharField(max_length=200)
    date = models.DateField()
    #cost = MoneyField(max_digits=10, decimal_places=2, default_currency='AUD')
    amount = models.DecimalField(max_digits=6, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CURRENCIES, default='AUD')
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)