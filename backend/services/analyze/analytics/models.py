from django.db import models
from django.contrib.postgres.fields import ArrayField
import uuid


SOURCE_TYPE_CHOICES = [
    ("code", "Code / PR / MR"),
    ("kanban", "Kanban board"),
    ("cicd", "CI/CD pipeline"),
]


class Dataset(models.Model):
    """
    Model to store uploaded CSV datasets
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.IntegerField(null=True, blank=True, db_index=True)
    workspace_id = models.IntegerField(null=True, blank=True, db_index=True)
    repository_id = models.IntegerField(null=True, blank=True, db_index=True)
    platform = models.CharField(max_length=50, default="gitlab")

    # Discriminator: which DevOps domain this dataset belongs to.
    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_TYPE_CHOICES,
        default="code",
        db_index=True,
    )
    # Free-form config for live-collected datasets so they can be refreshed:
    # {provider, board_id, workflow_id, since, until, ...}
    source_config = models.JSONField(default=dict, blank=True)
    # Back-link to the Collection row that produced this dataset (if live).
    collection_id = models.UUIDField(null=True, blank=True, db_index=True)

    filename = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    rows_count = models.IntegerField(default=0)
    columns_count = models.IntegerField(default=0)
    
    # Stockage des colonnes disponibles et leurs types
    columns_metadata = models.JSONField(
        default=dict,
        help_text="Metadata about columns: {column_name: {type: str, unique_values: int, ...}}"
    )
    
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


class DevOpsCollectionJob(models.Model):
    """
    Async background job that collects a Kanban / CI-CD dataset from a
    provider. Created by the *CollectView endpoints; updated by the worker
    thread; polled by the frontend progress page; published as a notification
    on completion.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In progress"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    SOURCE_CHOICES = [
        ("kanban", "Kanban board"),
        ("cicd", "CI/CD pipeline"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.IntegerField(null=True, blank=True, db_index=True)
    workspace_id = models.IntegerField(null=True, blank=True, db_index=True)
    repository_id = models.IntegerField(null=True, blank=True, db_index=True)

    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES, db_index=True)
    provider = models.CharField(max_length=50, blank=True, default="")
    label = models.CharField(max_length=255, blank=True, default="")

    # Captured for resume / debug. Tokens are NOT stored here.
    request_payload = models.JSONField(default=dict, blank=True)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True
    )
    progress_message = models.CharField(max_length=255, blank=True, default="")
    progress_percent = models.IntegerField(default=0)
    collected_items = models.IntegerField(default=0)
    total_items = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, default="")

    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="devops_jobs",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "devops_collection_jobs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_id", "-created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"DevOpsCollectionJob {self.id} ({self.source_type}/{self.status})"


class MetricDefinition(models.Model):
    """
    Définition des métriques disponibles pour l'analyse
    """
    CHART_TYPE_CHOICES = [
        ('line', 'Line Chart'),
        ('bar', 'Bar Chart'),
        ('scatter', 'Scatter Plot'),
        ('histogram', 'Histogram'),
        ('pie', 'Pie Chart'),
        ('heatmap', 'Heatmap'),
        ('box', 'Box Plot'),
        ('area', 'Area Chart'),
    ]
    
    AGGREGATION_CHOICES = [
        ('sum', 'Sum'),
        ('mean', 'Mean'),
        ('median', 'Median'),
        ('count', 'Count'),
        ('min', 'Min'),
        ('max', 'Max'),
        ('std', 'Standard Deviation'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=100, unique=True, help_text="Unique code identifier")
    name = models.CharField(max_length=200)
    description = models.TextField()

    # Which DevOps domain this metric belongs to. Used by /metrics/by_category/
    # to keep the code / kanban / cicd catalogs separate.
    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_TYPE_CHOICES,
        default="code",
        db_index=True,
    )

    # Configuration de la métrique
    category = models.CharField(max_length=50, help_text="Category: timeseries, distribution, correlation, etc.")
    default_chart_type = models.CharField(max_length=50, choices=CHART_TYPE_CHOICES)
    supported_chart_types = ArrayField(
        models.CharField(max_length=50),
        help_text="List of supported chart types for this metric"
    )
    
    # Colonnes requises
    required_columns = models.JSONField(
        help_text="List of required column patterns: ['Creation_Date', '#Commits']"
    )
    
    # Options de configuration
    supports_time_aggregation = models.BooleanField(default=False)
    supports_custom_axes = models.BooleanField(default=False)
    default_aggregation = models.CharField(
        max_length=20, 
        choices=AGGREGATION_CHOICES,
        null=True,
        blank=True
    )
    
    # Fonction d'analyse correspondante
    analysis_function = models.CharField(
        max_length=100,
        help_text="Name of the function in analysis_functions.py"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'metric_definitions'
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


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
    
    # Configuration de l'analyse
    metric_code = models.CharField(max_length=100, help_text="Code of the metric to analyze")
    chart_type = models.CharField(max_length=50, help_text="Type of chart to generate")
    
    # Configuration flexible pour les axes
    config = models.JSONField(
        default=dict,
        help_text="""Configuration: {
            'x_axis': 'column_name',
            'y_axis': 'column_name',
            'time_aggregation': 'D/W/M/Y',
            'aggregation': 'sum/mean/median',
            'filters': {...},
            'custom_params': {...}
        }"""
    )
    
    # DSL-First custom analysis fields
    dsl_config = models.JSONField(
        null=True,
        blank=True,
        help_text="Analysis DSL document (version 1) when analysis was generated via natural language."
    )
    nl_query = models.TextField(
        null=True,
        blank=True,
        help_text="Original natural-language query that produced this analysis."
    )
    custom_label = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="User-provided label for saved custom analyses."
    )
    is_custom = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True when this analysis was generated via the DSL/NL pipeline."
    )

    # Status et résultats
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    error_message = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "analyses"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['metric_code']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"Analysis {self.id} - {self.metric_code} - {self.status}"


class AnalysisResult(models.Model):
    """
    Model to store analysis results
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis = models.OneToOneField(
        Analysis, 
        on_delete=models.CASCADE, 
        related_name='result'
    )
    
    # Données pour graphes interactifs
    chart_data = models.JSONField(
        help_text="Data structure for interactive charts (plotly/recharts format)"
    )
    
    # Image matplotlib (optionnel)
    chart_image = models.TextField(
        null=True,
        blank=True,
        help_text="Base64 encoded matplotlib image"
    )
    
    # Statistiques supplémentaires
    statistics = models.JSONField(
        null=True,
        blank=True,
        help_text="Additional statistical information"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'analysis_results'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Result for Analysis {self.analysis_id}"


class AnalysisBatch(models.Model):
    """
    Model to group multiple analyses together
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('partial', 'Partially Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name='analysis_batches'
    )
    
    name = models.CharField(max_length=200, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    total_analyses = models.IntegerField(default=0)
    completed_analyses = models.IntegerField(default=0)
    failed_analyses = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'analysis_batches'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Batch {self.id} - {self.status}"


class BatchAnalysis(models.Model):
    """
    Relation entre un batch et ses analyses
    """
    batch = models.ForeignKey(
        AnalysisBatch,
        on_delete=models.CASCADE,
        related_name='batch_analyses'
    )
    analysis = models.ForeignKey(
        Analysis,
        on_delete=models.CASCADE,
        related_name='batch_memberships'
    )
    order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'batch_analyses'
        ordering = ['order']
        unique_together = ['batch', 'analysis']
