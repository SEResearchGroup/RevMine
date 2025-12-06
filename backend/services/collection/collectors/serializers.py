from rest_framework import serializers
from .models import CollectionPlan


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


class CollectionPlanSerializer(serializers.ModelSerializer):
    """
    Serializer for CollectionPlan model
    """
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
            'status',
            'created_at',
            'started_at',
            'completed_at',
            'selected_metrics',
            'filters',
            'total_items',
            'collected_items',
            'error_message',
        ]
        read_only_fields = ['id', 'created_at', 'started_at', 'completed_at']