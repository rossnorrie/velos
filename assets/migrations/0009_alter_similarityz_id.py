# Generated by Django 5.1.7 on 2025-03-25 17:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0008_alter_documentz_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='similarityz',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
    ]
