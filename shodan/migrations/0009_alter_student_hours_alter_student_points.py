# Generated by Django 5.1 on 2024-08-19 05:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shodan', '0008_student_hours_student_points'),
    ]

    operations = [
        migrations.AlterField(
            model_name='student',
            name='hours',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='student',
            name='points',
            field=models.IntegerField(default=0),
        ),
    ]
