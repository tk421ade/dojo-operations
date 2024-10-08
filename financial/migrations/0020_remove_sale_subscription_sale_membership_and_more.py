# Generated by Django 5.1 on 2024-09-04 02:02

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dojoconf', '0007_alter_address_latitude_alter_address_longitude'),
        ('financial', '0019_rename_subscription_product_membership_membership_product_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='sale',
            name='subscription',
        ),
        migrations.AddField(
            model_name='sale',
            name='membership',
            field=models.ForeignKey(blank=True, help_text='membership, Category or Event is required.', null=True, on_delete=django.db.models.deletion.CASCADE, to='financial.membership'),
        ),
        migrations.AlterField(
            model_name='membershipcustomfrequency',
            name='frequency',
            field=models.TextField(help_text="\n    Each row is a date. You can add ranges (i.e '2024-08-01 to 2024-08-30' or single days (i.e 2024-08-01))<br>\n    <br>\n    For example, to create a membership that will cover 4 payments, one per school holidays in 2024 in SA, \n    those will be the contents:<br>\n    2024-01-29 to 2024-04-12<br>\n    2024-04-29 to 2024-07-05<br>\n    2024-07-22 to 2024-09-27<br>\n    2024-10-14 to 2024-12-13<br>\n    "),
        ),
        migrations.AlterField(
            model_name='sale',
            name='category',
            field=models.ForeignKey(blank=True, help_text='membership, Category or Event is required.', null=True, on_delete=django.db.models.deletion.CASCADE, to='financial.category'),
        ),
        migrations.AlterField(
            model_name='sale',
            name='date_from',
            field=models.DateField(blank=True, help_text='Auto populated if type is membership and it is empty', null=True),
        ),
        migrations.AlterField(
            model_name='sale',
            name='date_to',
            field=models.DateField(blank=True, help_text='Auto populated if type is membership and it is empty', null=True),
        ),
        migrations.AlterField(
            model_name='sale',
            name='event',
            field=models.ForeignKey(blank=True, help_text='membership, Category or Event is required.', null=True, on_delete=django.db.models.deletion.CASCADE, to='dojoconf.event'),
        ),
    ]
