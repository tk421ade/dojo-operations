# Generated by Django 5.1 on 2024-08-20 05:29

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financial', '0008_remove_subscriptionproduct_custom_frequencies_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subscriptioncustomfrequency',
            name='subscription_product',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='financial.subscriptionproduct'),
        ),
    ]
