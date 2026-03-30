from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collectors', '0007_collection_is_external'),
    ]

    operations = [
        migrations.AddField(
            model_name='collection',
            name='cleaning_metadata',
            field=models.JSONField(
                blank=True,
                help_text='Pre-computed metadata for cleaning config (authors, extensions, item count)',
                null=True,
            ),
        ),
    ]
