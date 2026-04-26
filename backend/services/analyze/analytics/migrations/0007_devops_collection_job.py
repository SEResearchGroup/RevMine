"""
Async background job for Kanban / CI-CD collection — stores progress so the
frontend can poll a status endpoint and the user can navigate away while the
collection runs.
"""

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0006_seed_devops_metrics"),
    ]

    operations = [
        migrations.CreateModel(
            name="DevOpsCollectionJob",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("user_id", models.IntegerField(blank=True, db_index=True, null=True)),
                ("workspace_id", models.IntegerField(blank=True, db_index=True, null=True)),
                ("repository_id", models.IntegerField(blank=True, db_index=True, null=True)),
                (
                    "source_type",
                    models.CharField(
                        choices=[("kanban", "Kanban board"), ("cicd", "CI/CD pipeline")],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                ("provider", models.CharField(blank=True, default="", max_length=50)),
                ("label", models.CharField(blank=True, default="", max_length=255)),
                ("request_payload", models.JSONField(blank=True, default=dict)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("in_progress", "In progress"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("progress_message", models.CharField(blank=True, default="", max_length=255)),
                ("progress_percent", models.IntegerField(default=0)),
                ("collected_items", models.IntegerField(default=0)),
                ("total_items", models.IntegerField(default=0)),
                ("error_message", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "dataset",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="devops_jobs",
                        to="analytics.dataset",
                    ),
                ),
            ],
            options={
                "db_table": "devops_collection_jobs",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["user_id", "-created_at"],
                        name="devops_jobs_user_at_idx",
                    ),
                    models.Index(fields=["status"], name="devops_jobs_status_idx"),
                ],
            },
        ),
    ]
