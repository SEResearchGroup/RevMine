"""
backend/services/collection/collectors/models.py
"""
from django.db import models


class CollectionPlan(models.Model):
    """
    Represents a data collection plan for a repository
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    user = models.IntegerField(help_text="User ID from API Gateway")
    workspace_id = models.IntegerField(help_text="Workspace ID from Configuration Service")
    repository_id = models.IntegerField(help_text="Repository ID from Configuration Service")
    
    # Repository details (cached from Configuration Service)
    repository_name = models.CharField(max_length=255)
    repository_full_name = models.CharField(max_length=500)
    platform = models.CharField(max_length=20)
    repository_url = models.URLField(null=True, blank=True)
    default_branch = models.CharField(max_length=100, null=True, blank=True)
    
    # Store encrypted token
    token_encrypted = models.TextField(help_text="Encrypted access token" ,default=None)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Metrics and filters
    selected_metrics = models.JSONField(default=list, help_text="List of metrics to collect")
    filters = models.JSONField(default=dict, help_text="Collection filters")
    
    # Progress tracking
    total_items = models.IntegerField(default=0)
    collected_items = models.IntegerField(default=0)
    
    error_message = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'collection_plans'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Collection Plan {self.id} - {self.repository_full_name} ({self.status})"
    
    @property
    def progress_percentage(self):
        if self.total_items == 0:
            return 0
        return int((self.collected_items / self.total_items) * 100)


class CollectedData(models.Model):
    """
    Stores raw data collected from Git APIs
    """
    collection_plan = models.ForeignKey(
        CollectionPlan,
        on_delete=models.CASCADE,
        related_name='collected_data'
    )
    
    metric_type = models.CharField(
        max_length=50,
        help_text="Type of metric (pull_requests, commits, issues, etc.)"
    )
    
    raw_data = models.JSONField(help_text="Raw data from API")
    
    external_id = models.CharField(
        max_length=100,
        help_text="ID from GitHub/GitLab API"
    )
    
    collected_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'collected_data'
        ordering = ['-collected_at']
        unique_together = ['collection_plan', 'metric_type', 'external_id']
        indexes = [
            models.Index(fields=['collection_plan', 'metric_type']),
            models.Index(fields=['external_id']),
        ]
    
    def __str__(self):
        return f"{self.metric_type} - {self.external_id}"