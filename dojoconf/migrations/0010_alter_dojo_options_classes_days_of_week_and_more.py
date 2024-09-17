# Generated by Django 5.1 on 2024-09-17 08:17

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dojoconf', '0009_remove_interval_created_at_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='dojo',
            options={},
        ),
        migrations.AddField(
            model_name='classes',
            name='days_of_week',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(choices=[('monday', 'Monday'), ('tuesday', 'Tuesday'), ('wednesday', 'Wednesday'), ('thursday', 'Thursday'), ('friday', 'Friday'), ('saturday', 'Saturday'), ('sunday', 'Sunday')], max_length=9), default='{monday}', help_text='i.e "monday,tuesday". Accepted values: monday,tuesday,wednesday,thursday,friday,saturday,sunday"', size=None),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='classes',
            name='finishing_at',
            field=models.DateField(blank=True, help_text='The maximum value and the default is one year.', null=True),
        ),
        migrations.AddField(
            model_name='classes',
            name='starting_at',
            field=models.DateField(default='2024-09-27'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='classes',
            name='type',
            field=models.CharField(choices=[('weekly', 'Weekly')], default='weekly', help_text='i.e "Weekly"', max_length=9),
            preserve_default=False,
        ),
        migrations.DeleteModel(
            name='Interval',
        ),
    ]
