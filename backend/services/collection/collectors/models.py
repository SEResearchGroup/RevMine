from django.db import models


class CollectionPlan(models.Model):
    """
    Represents a data collection plan for a repository/project
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
    token_encrypted = models.TextField(help_text="Encrypted access token")
    
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
    
    # Statistics for summary
    stats = models.JSONField(
        default=dict,
        help_text="Collection statistics (commits_count, comments_count, etc.)"
    )
    
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
    Stores ALL raw data collected for a collection plan
    It contains collection plan insformation as a one-to-one relationship and a JSON field with all raw data
    """
    collection_plan = models.OneToOneField(
        CollectionPlan,
        on_delete=models.CASCADE,
        related_name='collected_data',
        primary_key=True
    )
    
    # All raw data organized by metric type
    raw_data = models.JSONField(
        help_text="All collected data organized by metric type: {pull_requests: [...], commits: [...], etc.}"
    )
    
    collected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'collected_data'
    
    def __str__(self):
        return f"Collected Data for Plan {self.collection_plan.id}"