# Generated by Django 3.1.3 on 2020-11-30 14:05

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cowsite', '0001_initial'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Cow_health',
        ),
        migrations.DeleteModel(
            name='Cow_info',
        ),
    ]
