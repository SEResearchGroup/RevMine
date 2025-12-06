"""
backend/services/collection/collectors/serializers.py
"""
from rest_framework import serializers
from .models import CollectionPlan, CollectedData


class StartCollectionSerializer(serializers.Serializer):
    """
    Serializer for starting a collection
    """
    repository_id = serializers.IntegerField(required=True)
    workspace_id = serializers.IntegerField(required=True)
    
    # Repository details from Configuration Service
    repository_name = serializers.CharField(required=True)
    repository_full_name = serializers.CharField(required=True)
    platform = serializers.CharField(required=True)
    repository_url = serializers.URLField(required=False)
    default_branch = serializers.CharField(required=False)
    
    # Token from workspace
    token = serializers.CharField(required=True, write_only=True)


class MetricsFilterSerializer(serializers.Serializer):
    """
    Serializer for metrics selection and filters
    """
    # Available metrics
    METRIC_CHOICES = [
        'pull_requests',
        'commits',
        'issues',
        'comments',
        'reviews',
    ]
    
    STATUS_CHOICES = ['open', 'closed', 'merged']
    
    selected_metrics = serializers.ListField(
        child=serializers.ChoiceField(choices=METRIC_CHOICES),
        required=True,
        min_length=1
    )
    
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    status = serializers.ListField(
        child=serializers.ChoiceField(choices=STATUS_CHOICES),
        required=False,
        allow_empty=True
    )
    
    def validate(self, data):
        """Validate that end_date is after start_date"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                "end_date must be after start_date"
            )
        
        return data


class CollectionPlanSerializer(serializers.ModelSerializer):
    """
    Serializer for CollectionPlan model
    """
    progress_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = CollectionPlan
        fields = [
            'id',
            'user',
            'workspace_id',
            'repository_id',
            'repository_name',
            'repository_full_name',
            'platform',
            'repository_url',
            'default_branch',
            'status',
            'created_at',
            'started_at',
            'completed_at',
            'selected_metrics',
            'filters',
            'total_items',
            'collected_items',
            'progress_percentage',
            'error_message',
        ]
        read_only_fields = [
            'id', 
            'created_at', 
            'started_at', 
            'completed_at',
            'progress_percentage'
        ]


class CollectedDataSerializer(serializers.ModelSerializer):
    """
    Serializer for CollectedData
    """
    class Meta:
        model = CollectedData
        fields = [
            'id',
            'collection_plan',
            'metric_type',
            'raw_data',
            'external_id',
            'collected_at',
        ]
        read_only_fields = ['id', 'collected_at']