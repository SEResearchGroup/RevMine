from rest_framework import serializers
from .models import Dataset, Analysis, AnalysisResult


class DatasetSerializer(serializers.ModelSerializer):
    """
    Serializer for Dataset model
    """

    class Meta:
        model = Dataset
        fields = [
            "id",
            "workspace_id",
            "repository_id",
            "filename",
            "rows_count",
            "columns_count",
            "platform",
            "uploaded_at",
            "updated_at",
        ]
        read_only_fields = ["id", "uploaded_at", "updated_at"]


class AnalysisResultSerializer(serializers.ModelSerializer):
    """
    Serializer for AnalysisResult model
    """

    class Meta:
        model = AnalysisResult
        fields = ["id", "chart_type", "chart_image", "chart_data", "created_at"]
        read_only_fields = ["id", "created_at"]


class AnalysisSerializer(serializers.ModelSerializer):
    """
    Serializer for Analysis model with nested results
    """

    results = AnalysisResultSerializer(many=True, read_only=True)
    dataset = DatasetSerializer(read_only=True)

    class Meta:
        model = Analysis
        fields = [
            "id",
            "dataset",
            "requested_charts",
            "status",
            "error_message",
            "created_at",
            "updated_at",
            "completed_at",
            "results",
        ]
        read_only_fields = [
            "id",
            "status",
            "error_message",
            "created_at",
            "updated_at",
            "completed_at",
        ]


class AnalysisCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a new analysis request
    """

    csv_file = serializers.FileField(required=True)
    workspace_id = serializers.IntegerField(required=False, allow_null=True)
    platform = serializers.ChoiceField(choices=["gitlab", "github"], default="gitlab")
    repository_id = serializers.IntegerField(required=False, allow_null=True)
    requested_charts = serializers.ListField(
        child=serializers.CharField(max_length=100), required=True, allow_empty=False
    )

    def validate_csv_file(self, value):
        """
        Validate that the uploaded file is a CSV
        """
        if not value.name.endswith(".csv"):
            raise serializers.ValidationError("File must be a CSV file")
        return value

    def validate_requested_charts(self, value):
        """
        Validate that requested charts are valid
        """
        valid_charts = [
            "commits_over_time",
            "mr_creation_timeline",
            "lead_time_distribution",
            "commits_distribution",
            "commiters_analysis",
            "commit_time_analysis",
            "code_churn",
            "churn_scatter",
            "mr_size_analysis",
            "discussions_analysis",
            "collaboration_metrics",
            "comments_analysis",
            "files_modified",
            "filetypes_distribution",
            "entropy_analysis",
            "state_distribution",
            "rework_analysis",
            "correlation_matrix",
            "mr_complexity",
            "project_comparison",
        ]

        invalid_charts = [chart for chart in value if chart not in valid_charts]
        if invalid_charts:
            raise serializers.ValidationError(
                f"Invalid chart types: {', '.join(invalid_charts)}"
            )

        return value


class AnalysisListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for listing analyses
    """

    dataset_filename = serializers.CharField(source="dataset.filename", read_only=True)
    results_count = serializers.SerializerMethodField()

    class Meta:
        model = Analysis
        fields = [
            "id",
            "dataset_filename",
            "requested_charts",
            "status",
            "created_at",
            "completed_at",
            "results_count",
        ]

    def get_results_count(self, obj):
        return obj.results.count()
