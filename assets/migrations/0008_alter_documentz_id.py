# Generated by Django 5.1.7 on 2025-03-25 17:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0007_remove_documentz_temp_field'),
    ]

    operations = [
        migrations.AlterField(
            model_name='documentz',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
    ]
