# Generated by Django 5.1 on 2024-09-04 01:58

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dojoconf', '0007_alter_address_latitude_alter_address_longitude'),
        ('financial', '0015_expense_amount_expense_category_expense_currency'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='SubscriptionProduct',
            new_name='MembershipProduct',
        ),
    ]
