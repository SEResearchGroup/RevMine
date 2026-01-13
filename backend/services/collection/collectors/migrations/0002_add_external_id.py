# Generated migration for adding external_id field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collectors', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='collection',
            name='external_id',
            field=models.CharField(
                blank=True,
                help_text='External platform ID (e.g., GitLab project ID)',
                max_length=100,
                null=True,
            ),
        ),
    ]
