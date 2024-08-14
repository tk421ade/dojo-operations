# Generated by Django 5.1 on 2024-08-13 05:42

import datetime
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shodan', '0013_rename_events_event'),
    ]

    operations = [
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
                ('classes', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='shodan.classes')),
                ('dojo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='shodan.dojo')),
                ('event', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='shodan.event')),
            ],
        ),
    ]
