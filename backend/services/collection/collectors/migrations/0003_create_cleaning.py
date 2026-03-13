# Generated migration for Cleaning model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("collectors", "0002_add_external_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="Cleaning",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "start_date",
                    models.DateField(
                        blank=True,
                        help_text="Start date for cleaning filter",
                        null=True,
                    ),
                ),
                (
                    "end_date",
                    models.DateField(
                        blank=True, help_text="End date for cleaning filter", null=True
                    ),
                ),
                (
                    "filters",
                    models.JSONField(
                        default=dict, help_text="Cleaning filters configuration"
                    ),
                ),
                (
                    "structured_csv_filename",
                    models.CharField(
                        blank=True,
                        help_text="Filename in MinIO for structured CSV",
                        max_length=500,
                        null=True,
                    ),
                ),
                (
                    "statistics_csv_filename",
                    models.CharField(
                        blank=True,
                        help_text="Filename in MinIO for statistics CSV",
                        max_length=500,
                        null=True,
                    ),
                ),
                (
                    "stats",
                    models.JSONField(default=dict, help_text="Cleaning statistics"),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("in_progress", "In Progress"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("error_message", models.TextField(blank=True, null=True)),
                (
                    "collection",
                    models.ForeignKey(
                        help_text="The collection this cleaning belongs to",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cleanings",
                        to="collectors.collection",
                    ),
                ),
            ],
            options={
                "db_table": "cleanings",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="cleaning",
            index=models.Index(
                fields=["collection", "status"], name="cleanings_collect_idx"
            ),
        ),
    ]
