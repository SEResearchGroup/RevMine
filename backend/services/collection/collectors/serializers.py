from rest_framework import serializers
from .models import Collection, CleanedData


class StartCollectionSerializer(serializers.Serializer):
    """Serializer for starting a collection."""

    repository_id = serializers.IntegerField(required=True)
    workspace_id = serializers.IntegerField(required=True)
    repository_name = serializers.CharField(required=True)
    repository_full_name = serializers.CharField(required=True)
    platform = serializers.CharField(required=True)
    repository_url = serializers.URLField(required=False)
    default_branch = serializers.CharField(required=False)
    external_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    
    token = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)


class MetricsFilterSerializer(serializers.Serializer):
    """Serializer for metrics and filters configuration."""

    selected_metrics = serializers.ListField(
        child=serializers.CharField(), required=True, min_length=1
    )

    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    status = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )

    branch_name = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    save_batch_size = serializers.IntegerField(
        required=False, default=1, min_value=1, max_value=100
    )

    def validate(self, data):
        """Validate that end_date is after start_date"""
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError("end_date must be after start_date")

        return data


class CollectionSerializer(serializers.ModelSerializer):
    """Serializer for Collection model."""

    progress_percentage = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    can_resume = serializers.ReadOnlyField()

    class Meta:
        model = Collection
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
            'external_id',
            'branch_name',
            'status',
            'created_at',
            'started_at',
            'completed_at',
            'selected_metrics',
            'filters',
            'total_items',
            'collected_items',
            'save_batch_size',
            'is_total_approximate',
            'progress_percentage',
            'is_active',
            'can_resume',
            'last_collected_item_id',
            'stats',
            'error_message',
            'raw_data_filename',
            'is_external',
        ]
        read_only_fields = [
            "id",
            "created_at",
            "started_at",
            "completed_at",
            "progress_percentage",
            "is_active",
            "can_resume",
            "raw_data_filename",
        ]


class CleanedDataSerializer(serializers.ModelSerializer):
    """Serializer for CleanedData model."""

    collection_id = serializers.IntegerField(source="collection.id", read_only=True)
    platform = serializers.SerializerMethodField()

    class Meta:
        model = CleanedData
        fields = [
            "id",
            "collection_id",
            "platform",  # <-- ici
            "created_at",
            "completed_at",
            "start_date",
            "end_date",
            "filters",
            "selected_features",
            "structured_csv_filename",
            "statistics_csv_filename",
            "stats",
            "status",
            "error_message",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "completed_at",
        ]

    def get_platform(self, obj):
        if obj.collection:
            return obj.collection.platform
        return None


class CreateCleanedDataSerializer(serializers.Serializer):
    """Serializer for creating cleaned data."""

    collection_id = serializers.IntegerField(required=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    filters = serializers.JSONField(required=False, default=dict)
    selected_features = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text="List of feature IDs to include in statistics CSV",
    )

    def validate(self, data):
        """Validate cleaning parameters"""
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError("end_date must be after start_date")

        return data
