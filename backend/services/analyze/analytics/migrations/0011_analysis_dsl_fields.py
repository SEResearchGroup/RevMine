from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0010_remove_dataset_user_id_extra_index"),
    ]

    operations = [
        migrations.AddField(
            model_name="analysis",
            name="dsl_config",
            field=models.JSONField(
                blank=True,
                null=True,
                help_text="Analysis DSL document (version 1) when analysis was generated via natural language.",
            ),
        ),
        migrations.AddField(
            model_name="analysis",
            name="nl_query",
            field=models.TextField(
                blank=True,
                null=True,
                help_text="Original natural-language query that produced this analysis.",
            ),
        ),
        migrations.AddField(
            model_name="analysis",
            name="custom_label",
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                help_text="User-provided label for saved custom analyses.",
            ),
        ),
        migrations.AddField(
            model_name="analysis",
            name="is_custom",
            field=models.BooleanField(
                default=False,
                db_index=True,
                help_text="True when this analysis was generated via the DSL/NL pipeline.",
            ),
        ),
    ]
