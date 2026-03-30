from django.db import models


class Collection(models.Model):
    """
    Represents a data collection process for a repository.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('paused', 'Paused'),
    ]
    
    # Statuses that indicate an "active" collection (currently running)
    # Note: 'paused' and 'failed' are NOT active - they allow new collections to start
    ACTIVE_STATUSES = ['pending', 'in_progress']
    
    user = models.IntegerField(help_text="User ID from API Gateway")
    workspace_id = models.IntegerField(help_text="Workspace ID from Configuration Service")
    repository_id = models.IntegerField(help_text="Repository ID from Configuration Service")
    
    repository_name = models.CharField(max_length=255)
    repository_full_name = models.CharField(max_length=500)
    platform = models.CharField(max_length=20)
    repository_url = models.URLField(null=True, blank=True)
    default_branch = models.CharField(max_length=100, null=True, blank=True)
    external_id = models.CharField(
        max_length=100, 
        null=True, 
        blank=True,
        help_text="External platform ID (e.g., GitLab project ID)"
    )
    
    branch_name = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text="Branch to collect data from"
    )
    
    token_encrypted = models.TextField(help_text="Encrypted access token")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    paused_at = models.DateTimeField(null=True, blank=True)
    
    selected_metrics = models.JSONField(default=list, help_text="List of metrics to collect")
    filters = models.JSONField(default=dict, help_text="Collection filters")
    
    total_items = models.IntegerField(default=0)
    collected_items = models.IntegerField(default=0)
    
    # Track last collected item for resume capability
    last_collected_item_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Last PR/MR number collected (for resume)"
    )
    
    # Store MinIO filename for raw JSON data
    raw_data_filename = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Filename in MinIO for raw JSON data"
    )
    
    # Structured CSV filename
    structured_csv_filename = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Filename in MinIO for structured CSV"
    )
    
    # Statistics CSV filename
    statistics_csv_filename = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Filename in MinIO for statistics CSV"
    )
    
    stats = models.JSONField(
        default=dict,
        help_text="Collection statistics"
    )
    
    error_message = models.TextField(null=True, blank=True)
    
    is_external = models.BooleanField(
        default=False,
        help_text="Whether this collection was uploaded externally by the user"
    )
    
    cleaning_metadata = models.JSONField(
        null=True,
        blank=True,
        help_text="Pre-computed metadata for cleaning config (authors, extensions, item count)"
    )
    
    class Meta:
        db_table = 'collections' 
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'repository_id']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Collection {self.id} - {self.repository_full_name} ({self.status})"
    
    @property
    def progress_percentage(self):
        if self.total_items == 0:
            return 0
        return int((self.collected_items / self.total_items) * 100)
    
    @property
    def can_resume(self):
        """Check if collection can be resumed.
        
        A collection can be resumed if:
        - It's paused/failed and has a last_collected_item_id
        - It's in_progress but has data (orphaned after container restart/breakdown)
        """
        if self.status in ['paused', 'failed'] and self.last_collected_item_id is not None:
            return True
        # Orphaned in_progress collections can also be resumed if they have progress
        if self.status == 'in_progress' and self.last_collected_item_id is not None:
            return True
        return False
    
    @property
    def is_active(self):
        """Check if collection is in an active (non-completed) state"""
        return self.status in self.ACTIVE_STATUSES
    
    @classmethod
    def get_active_for_repository(cls, user_id, repository_id):
        """
        Get any active (non-completed, non-failed) collection for a user's repository.
        Used to prevent duplicate collection creation.
        """
        return cls.objects.filter(
            user=user_id,
            repository_id=repository_id,
            status__in=cls.ACTIVE_STATUSES
        ).first()


class CleanedData(models.Model):
    """
    Represents a data cleaning/filtering operation on a collection.
    A collection can have multiple cleaned data instances with different configurations.
    """
    collection = models.ForeignKey(
        Collection,
        on_delete=models.CASCADE,
        related_name='cleaned_data',
        help_text="The collection this cleaned data belongs to"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Date range filters for cleaning (subset of collection data)
    start_date = models.DateField(null=True, blank=True, help_text="Start date for cleaning filter")
    end_date = models.DateField(null=True, blank=True, help_text="End date for cleaning filter")
    
    # Cleaning configuration
    filters = models.JSONField(default=dict, help_text="Cleaning filters configuration")
    selected_features = models.JSONField(
        default=list,
        help_text="List of feature IDs to include in statistics CSV"
    )
    
    # Output files in MinIO
    structured_csv_filename = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Filename in MinIO for structured CSV"
    )
    
    statistics_csv_filename = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Filename in MinIO for statistics CSV"
    )
    
    # Statistics
    stats = models.JSONField(
        default=dict,
        help_text="Cleaning statistics"
    )
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    
    error_message = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'cleaned_data'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['collection', 'status']),
        ]
    
    def __str__(self):
        return f"CleanedData {self.id} for Collection {self.collection_id} ({self.status})"
