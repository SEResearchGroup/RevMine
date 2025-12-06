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
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Will be used later for metrics and filters
    selected_metrics = models.JSONField(null=True, blank=True, help_text="List of metrics to collect")
    filters = models.JSONField(null=True, blank=True, help_text="Collection filters")
    
    # Progress tracking
    total_items = models.IntegerField(default=0)
    collected_items = models.IntegerField(default=0)
    
    error_message = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'collection_plans'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Collection Plan {self.id} - {self.repository_full_name} ({self.status})"