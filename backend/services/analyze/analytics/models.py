from django.db import models
from django.contrib.postgres.fields import ArrayField
import uuid


class Dataset(models.Model):
    """
    Model to store uploaded CSV datasets
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace_id = models.IntegerField(null=True, blank=True, db_index=True)
    repository_id = models.IntegerField(null=True, blank=True, db_index=True)
    platform = models.CharField(max_length=50, default="gitlab")

    filename = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    rows_count = models.IntegerField(default=0)
    columns_count = models.IntegerField(default=0)

    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "datasets"
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["workspace_id", "repository_id"]),
            models.Index(fields=["-uploaded_at"]),
        ]

    def __str__(self):
        return f"{self.filename} - {self.id}"


class Analysis(models.Model):
    """
    Model to store analysis requests and results
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dataset = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name="analyses"
    )

    # Analysis configuration
    requested_charts = ArrayField(
        models.CharField(max_length=100), help_text="List of requested chart types"
    )

    # Analysis status and results
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    error_message = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "analyses"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"Analysis {self.id} - {self.status}"


class AnalysisResult(models.Model):
    """
    Model to store individual chart results for each analysis
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis = models.ForeignKey(
        Analysis, on_delete=models.CASCADE, related_name="results"
    )

    chart_type = models.CharField(max_length=100)
    chart_image = models.TextField(help_text="Base64 encoded image")
    chart_data = models.JSONField(
        null=True, blank=True, help_text="Additional data or statistics for the chart"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "analysis_results"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["analysis", "chart_type"]),
        ]

    def __str__(self):
        return f"{self.chart_type} - Analysis {self.analysis_id}"
