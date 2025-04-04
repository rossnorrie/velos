# Generated by Django 5.1.7 on 2025-03-25 17:46

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0011_remove_documentz_temp_remove_similarityz_temp'),
    ]

    operations = [
        migrations.AlterField(
            model_name='similarityz',
            name='doc1',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sim_as_doc1', to='assets.documentz'),
        ),
        migrations.AlterField(
            model_name='similarityz',
            name='doc2',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sim_as_doc2', to='assets.documentz'),
        ),
    ]
