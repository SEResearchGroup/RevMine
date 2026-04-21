"""
Add source_type discriminator to Dataset and MetricDefinition so Kanban and
CI/CD DevOps analyses can live alongside the existing code/PR analyses without
leaking metric catalogs across domains.
"""

from django.db import migrations, models


SOURCE_TYPE_CHOICES = [
    ("code", "code"),
    ("kanban", "kanban"),
    ("cicd", "cicd"),
]


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0004_add_top_charts_remove_custom"),
    ]

    operations = [
        migrations.AddField(
            model_name="dataset",
            name="source_type",
            field=models.CharField(
                choices=SOURCE_TYPE_CHOICES,
                default="code",
                max_length=20,
                db_index=True,
            ),
        ),
        migrations.AddField(
            model_name="dataset",
            name="source_config",
            field=models.JSONField(
                default=dict,
                blank=True,
                help_text="Live-collection config: {provider, board_id, workflow_id, since, until}",
            ),
        ),
        migrations.AddField(
            model_name="dataset",
            name="collection_id",
            field=models.UUIDField(null=True, blank=True, db_index=True),
        ),
        migrations.AddField(
            model_name="metricdefinition",
            name="source_type",
            field=models.CharField(
                choices=SOURCE_TYPE_CHOICES,
                default="code",
                max_length=20,
                db_index=True,
            ),
        ),
    ]
