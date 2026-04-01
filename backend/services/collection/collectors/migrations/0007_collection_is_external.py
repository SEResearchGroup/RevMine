from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collectors', '0006_cleaneddata_selected_features'),
    ]

    operations = [
        migrations.AddField(
            model_name='collection',
            name='is_external',
            field=models.BooleanField(default=False, help_text='Whether this collection was uploaded externally by the user'),
        ),
    ]
