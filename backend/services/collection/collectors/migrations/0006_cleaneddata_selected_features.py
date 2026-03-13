# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "collectors",
            "0005_rename_cleanings_collect_idx_cleaned_dat_collect_2a8a5c_idx_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="cleaneddata",
            name="selected_features",
            field=models.JSONField(
                default=list,
                help_text="List of feature IDs to include in statistics CSV",
            ),
        ),
    ]
