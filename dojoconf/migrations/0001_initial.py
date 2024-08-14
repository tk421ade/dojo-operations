# Generated by Django 5.1 on 2024-08-14 07:25

import datetime
import django.contrib.postgres.fields
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Dojo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('email', models.EmailField(max_length=200)),
                ('created_at', models.DateTimeField(default=datetime.datetime.now)),
                ('updated_at', models.DateTimeField(blank=True, null=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Friendly name', max_length=200)),
                ('street', models.CharField(max_length=255)),
                ('city', models.CharField(max_length=100)),
                ('state', models.CharField(max_length=100)),
                ('zip_code', models.CharField(max_length=20)),
                ('country', models.CharField(max_length=100)),
                ('latitude', models.DecimalField(blank=True, decimal_places=15, max_digits=20, null=True)),
                ('longitude', models.DecimalField(blank=True, decimal_places=15, max_digits=20, null=True)),
                ('created_at', models.DateTimeField(default=datetime.datetime.now)),
                ('updated_at', models.DateTimeField(blank=True, null=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('dojo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dojoconf.dojo')),
            ],
        ),
        migrations.CreateModel(
            name='Interval',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='i.e "Every Monday"', max_length=200)),
                ('type', models.CharField(choices=[('weekly', 'Weekly')], help_text='i.e "Weekly"', max_length=9)),
                ('days_of_week', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(choices=[('monday', 'Monday'), ('tuesday', 'Tuesday'), ('wednesday', 'Wednesday'), ('thursday', 'Thursday'), ('friday', 'Friday'), ('saturday', 'Saturday'), ('sunday', 'Sunday')], max_length=9), help_text='i.e "monday,tuesday". Accepted values: monday,tuesday,wednesday,thursday,friday,saturday,sunday"', size=None)),
                ('starting_at', models.DateField()),
                ('finishing_at', models.DateField(blank=True, help_text='The maximum value and the default is one year.', null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(default=datetime.datetime.now)),
                ('updated_at', models.DateTimeField(blank=True, null=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('dojo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dojoconf.dojo')),
            ],
            options={
                'verbose_name': 'Class Interval',
                'verbose_name_plural': 'Class Intervals',
            },
        ),
        migrations.CreateModel(
            name='Classes',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='i.e "Adults"', max_length=200)),
                ('time_from', models.TimeField(help_text='i.e "Starting Local Time"')),
                ('time_to', models.TimeField(help_text='i.e "Finishing Local Time"')),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(default=datetime.datetime.now)),
                ('updated_at', models.DateTimeField(blank=True, null=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('address', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dojoconf.address')),
                ('dojo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dojoconf.dojo')),
                ('interval', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dojoconf.interval')),
            ],
        ),
    ]
