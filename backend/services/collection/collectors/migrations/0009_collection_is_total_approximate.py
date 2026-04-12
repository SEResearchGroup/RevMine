from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collectors', '0008_collection_cleaning_metadata'),
    ]

    operations = [
        migrations.AddField(
            model_name='collection',
            name='is_total_approximate',
            field=models.BooleanField(
                default=False,
                help_text='Whether the total_items count is approximate (e.g. GitHub with date filters)',
            ),
        ),
    ]
