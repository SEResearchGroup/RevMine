# Generated for qualitative analysis support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collectors', '0010_add_save_batch_size'),
    ]

    operations = [
        migrations.AddField(
            model_name='collection',
            name='for_qualitative',
            field=models.BooleanField(
                default=False,
                help_text=(
                    'If True, collect the complete review dataset (all endpoints + '
                    'thread resolution + reactions) for downstream qualitative analysis'
                ),
            ),
        ),
        migrations.AddField(
            model_name='collection',
            name='qualitative_data_filename',
            field=models.CharField(
                blank=True,
                help_text='Filename in MinIO for the complete qualitative JSON dataset',
                max_length=500,
                null=True,
            ),
        ),
    ]
