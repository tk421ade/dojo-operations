# Generated by Django 5.1 on 2024-08-20 05:08

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dojoconf', '0006_dojo_hostname'),
        ('financial', '0003_alter_expense_event_alter_sale_event'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Subscription',
            new_name='SubscriptionProduct',
        ),
    ]
