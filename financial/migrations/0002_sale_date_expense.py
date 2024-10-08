# Generated by Django 5.1 on 2024-08-14 08:43

import datetime
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dojoconf', '0001_initial'),
        ('financial', '0001_initial'),
        ('shodan', '0006_event_duration_event_time_from_event_time_to'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='date',
            field=models.DateField(default='2024-08-14'),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name='Expense',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('date', models.DateField()),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(default=datetime.datetime.now)),
                ('updated_at', models.DateTimeField(blank=True, null=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('dojo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dojoconf.dojo')),
                ('event', models.ForeignKey(blank=True, help_text='Optional, if related with an event.', null=True, on_delete=django.db.models.deletion.CASCADE, to='shodan.event')),
            ],
        ),
    ]
