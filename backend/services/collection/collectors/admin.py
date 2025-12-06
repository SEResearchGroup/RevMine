"""
backend/services/collection/collectors/admin.py
"""
from django.contrib import admin
from .models import CollectionPlan, CollectedData


@admin.register(CollectionPlan)
class CollectionPlanAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'repository_full_name',
        'platform',
        'status',
        'user',
        'created_at',
        'progress_percentage',
        'collected_items',
        'total_items'
    ]
    list_filter = ['status', 'platform', 'created_at']
    search_fields = ['repository_name', 'repository_full_name', 'user']
    readonly_fields = ['created_at', 'started_at', 'completed_at', 'progress_percentage']
    
    fieldsets = (
        ('Repository Information', {
            'fields': ('user', 'workspace_id', 'repository_id', 'repository_name', 
                      'repository_full_name', 'platform', 'repository_url', 'default_branch')
        }),
        ('Collection Status', {
            'fields': ('status', 'created_at', 'started_at', 'completed_at', 'progress_percentage')
        }),
        ('Collection Configuration', {
            'fields': ('selected_metrics', 'filters', 'token_encrypted')
        }),
        ('Progress', {
            'fields': ('total_items', 'collected_items', 'error_message')
        }),
    )


@admin.register(CollectedData)
class CollectedDataAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'collection_plan',
        'metric_type',
        'external_id',
        'collected_at'
    ]
    list_filter = ['metric_type', 'collected_at']
    search_fields = ['external_id', 'collection_plan__repository_full_name']
    readonly_fields = ['collected_at']
    
    fieldsets = (
        ('Collection Info', {
            'fields': ('collection_plan', 'metric_type', 'external_id')
        }),
        ('Data', {
            'fields': ('raw_data', 'collected_at')
        }),
    )