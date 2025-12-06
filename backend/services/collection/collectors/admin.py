from django.contrib import admin
from .models import CollectionPlan


@admin.register(CollectionPlan)
class CollectionPlanAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'repository_full_name',
        'platform',
        'status',
        'user',
        'created_at',
        'collected_items',
        'total_items'
    ]
    list_filter = ['status', 'platform', 'created_at']
    search_fields = ['repository_name', 'repository_full_name', 'user']
    readonly_fields = ['created_at', 'started_at', 'completed_at']
    
    fieldsets = (
        ('Repository Information', {
            'fields': ('user', 'workspace_id', 'repository_id', 'repository_name', 'repository_full_name', 'platform')
        }),
        ('Collection Status', {
            'fields': ('status', 'created_at', 'started_at', 'completed_at')
        }),
        ('Collection Configuration', {
            'fields': ('selected_metrics', 'filters')
        }),
        ('Progress', {
            'fields': ('total_items', 'collected_items', 'error_message')
        }),
    )