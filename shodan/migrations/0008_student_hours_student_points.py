# Generated by Django 5.1 on 2024-08-19 05:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shodan', '0007_alter_session_event_delete_event'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='hours',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='student',
            name='points',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
