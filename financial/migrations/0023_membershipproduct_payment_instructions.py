# Generated by Django 5.1 on 2024-09-10 07:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financial', '0022_membershipcustomfrequency'),
    ]

    operations = [
        migrations.AddField(
            model_name='membershipproduct',
            name='payment_instructions',
            field=models.TextField(blank=True, null=True),
        ),
    ]
