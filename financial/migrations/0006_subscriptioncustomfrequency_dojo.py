# Generated by Django 5.1 on 2024-08-20 05:18

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dojoconf', '0006_dojo_hostname'),
        ('financial', '0005_subscriptioncustomfrequency_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscriptioncustomfrequency',
            name='dojo',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='dojoconf.dojo'),
            preserve_default=False,
        ),
    ]
