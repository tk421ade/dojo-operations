# Generated by Django 5.1 on 2024-09-17 07:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shodan', '0018_student_address1_student_address2_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='start',
            field=models.DateField(blank=True, null=True),
        ),
    ]
