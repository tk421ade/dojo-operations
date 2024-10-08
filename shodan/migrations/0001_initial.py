# Generated by Django 5.1 on 2024-08-14 07:25

import datetime
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('dojoconf', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='i.e "Adults"', max_length=200)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(default=datetime.datetime.now)),
                ('updated_at', models.DateTimeField(blank=True, null=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('address', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dojoconf.address')),
                ('dojo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dojoconf.dojo')),
            ],
        ),
        migrations.CreateModel(
            name='Session',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='i.e "Adults Monday Session" or "Oct 2024 Seminar"', max_length=200)),
                ('date', models.DateField()),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(default=datetime.datetime.now)),
                ('updated_at', models.DateTimeField(blank=True, null=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('classes', models.ForeignKey(blank=True, help_text='Event or Classes needs to be defined', null=True, on_delete=django.db.models.deletion.CASCADE, to='dojoconf.classes')),
                ('dojo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dojoconf.dojo')),
                ('event', models.ForeignKey(blank=True, help_text='Event or Classes needs to be defined', null=True, on_delete=django.db.models.deletion.CASCADE, to='shodan.event')),
            ],
        ),
        migrations.CreateModel(
            name='Student',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('active', 'ACTIVE'), ('inactive', 'INACTIVE')], max_length=9)),
                ('name', models.CharField(max_length=200)),
                ('email', models.EmailField(max_length=200)),
                ('kyu', models.IntegerField(blank=True, null=True)),
                ('dan', models.IntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(default=datetime.datetime.now)),
                ('updated_at', models.DateTimeField(blank=True, null=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('dojo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dojoconf.dojo')),
            ],
        ),
        migrations.CreateModel(
            name='Attendance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('minutes', models.IntegerField(blank=True, null=True)),
                ('points', models.IntegerField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(default=datetime.datetime.now)),
                ('updated_at', models.DateTimeField(blank=True, null=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('dojo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dojoconf.dojo')),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='shodan.session')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='shodan.student')),
            ],
        ),
    ]
