from .dataset_services import DatasetService
from rest_framework import serializers
from .models import Dataset, MetricDefinition, Analysis, AnalysisResult, AnalysisBatch, BatchAnalysis
import pandas as pd
import json
from .analysis_service import AnalysisService


class DatasetSerializer(serializers.ModelSerializer):
    """Serializer for Dataset model"""
    
    class Meta:
        model = Dataset
        fields = [
            'id', 'workspace_id', 'repository_id', 'platform',
            'filename', 'file_path', 'rows_count', 'columns_count',
            'columns_metadata', 'uploaded_at', 'updated_at'
        ]
        read_only_fields = ['id', 'uploaded_at', 'updated_at']


class DatasetUploadSerializer(serializers.Serializer):
    """Serializer for handling dataset upload"""
    file = serializers.FileField()
    workspace_id = serializers.IntegerField(required=False, allow_null=True)
    repository_id = serializers.IntegerField(required=False, allow_null=True)
    platform = serializers.CharField(max_length=50, default='gitlab')
    
    def validate_file(self, value):
        """Validate that the file is a CSV"""
        if not value.name.endswith('.csv'):
            raise serializers.ValidationError("Only CSV files are supported")
        return value
    
    def create(self, validated_data):
        """Create a Dataset instance and process the CSV file"""
        
        file = validated_data.pop('file')
        service = DatasetService()
        dataset = service.create_dataset(file, **validated_data)
        
        return dataset


class DatasetColumnsSerializer(serializers.Serializer):
    """Serializer for dataset columns information"""
    columns = serializers.ListField(child=serializers.CharField())
    columns_metadata = serializers.JSONField()
    
    class Meta:
        fields = ['columns', 'columns_metadata']


class MetricDefinitionSerializer(serializers.ModelSerializer):
    """Serializer for MetricDefinition model"""
    
    class Meta:
        model = MetricDefinition
        fields = [
            'id', 'code', 'name', 'description', 'category',
            'default_chart_type', 'supported_chart_types',
            'required_columns', 'supports_time_aggregation',
            'supports_custom_axes', 'default_aggregation',
            'is_active'
        ]
        read_only_fields = ['id']


class AvailableMetricsSerializer(serializers.Serializer):
    """Serializer for available metrics based on dataset columns"""
    available_metrics = MetricDefinitionSerializer(many=True)
    dataset_columns = serializers.ListField(child=serializers.CharField())
    missing_columns_by_metric = serializers.DictField()


class AnalysisConfigSerializer(serializers.Serializer):
    """Serializer for analysis configuration"""
    x_axis = serializers.CharField(required=False, allow_null=True)
    y_axis = serializers.CharField(required=False, allow_null=True)
    time_aggregation = serializers.ChoiceField(
        choices=['D', 'W', 'M', 'Q', 'Y'],
        required=False,
        allow_null=True
    )
    aggregation = serializers.ChoiceField(
        choices=['sum', 'mean', 'median', 'count', 'min', 'max', 'std'],
        required=False,
        allow_null=True
    )
    filters = serializers.JSONField(required=False, allow_null=True)
    custom_params = serializers.JSONField(required=False, allow_null=True)


class AnalysisCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating an analysis"""
    config = AnalysisConfigSerializer(required=False)
    
    class Meta:
        model = Analysis
        fields = [
            'dataset', 'metric_code', 'chart_type', 'config'
        ]
    
    def validate(self, data):
        """Validate that the metric exists and chart type is supported"""
        metric_code = data.get('metric_code')
        chart_type = data.get('chart_type')
        
        try:
            metric = MetricDefinition.objects.get(code=metric_code, is_active=True)
        except MetricDefinition.DoesNotExist:
            raise serializers.ValidationError(
                f"Metric with code '{metric_code}' does not exist or is not active"
            )
        
        if chart_type not in metric.supported_chart_types:
            raise serializers.ValidationError(
                f"Chart type '{chart_type}' is not supported for metric '{metric_code}'. "
                f"Supported types: {', '.join(metric.supported_chart_types)}"
            )
        
        # Validate required columns exist in dataset
        dataset = data.get('dataset')
        if dataset:
            service = DatasetService()
            available_columns = service.get_columns(dataset)
            
            for required_col in metric.required_columns:
                if required_col not in available_columns:
                    raise serializers.ValidationError(
                        f"Required column '{required_col}' not found in dataset. "
                        f"Available columns: {', '.join(available_columns)}"
                    )
        
        return data
    
    def create(self, validated_data):
        """Create analysis and trigger processing"""
        config = validated_data.pop('config', {})
        analysis = Analysis.objects.create(config=config, **validated_data)
        
        # Trigger async processing
        from .tasks import process_analysis
        process_analysis.delay(str(analysis.id))
        
        return analysis


class AnalysisResultSerializer(serializers.ModelSerializer):
    """Serializer for AnalysisResult model"""
    
    class Meta:
        model = AnalysisResult
        fields = [
            'id', 'analysis', 'chart_data', 'chart_image',
            'statistics', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class AnalysisSerializer(serializers.ModelSerializer):
    """Serializer for Analysis model with results"""
    result = AnalysisResultSerializer(read_only=True)
    
    class Meta:
        model = Analysis
        fields = [
            'id', 'dataset', 'metric_code', 'chart_type', 'config',
            'status', 'error_message', 'result',
            'created_at', 'updated_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'status', 'error_message', 'result',
            'created_at', 'updated_at', 'completed_at'
        ]


class AnalysisListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing analyses"""
    
    class Meta:
        model = Analysis
        fields = [
            'id', 'dataset', 'metric_code', 'chart_type',
            'status', 'created_at', 'completed_at'
        ]
        read_only_fields = fields


class BatchAnalysisItemSerializer(serializers.Serializer):
    """Serializer for individual analysis in a batch"""
    metric_code = serializers.CharField()
    chart_type = serializers.CharField()
    config = AnalysisConfigSerializer(required=False)


class AnalysisBatchCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a batch of analyses"""
    analyses = BatchAnalysisItemSerializer(many=True)
    
    class Meta:
        model = AnalysisBatch
        fields = ['dataset', 'name', 'description', 'analyses']
    
    def create(self, validated_data):
        """Create batch and all associated analyses"""
        analyses_data = validated_data.pop('analyses')
        batch = AnalysisBatch.objects.create(**validated_data)
        batch.total_analyses = len(analyses_data)
        batch.save()
        
        # Create all analyses
        service = AnalysisService()
        
        for idx, analysis_data in enumerate(analyses_data):
            analysis = Analysis.objects.create(
                dataset=batch.dataset,
                metric_code=analysis_data['metric_code'],
                chart_type=analysis_data['chart_type'],
                config=analysis_data.get('config', {})
            )
            
            BatchAnalysis.objects.create(
                batch=batch,
                analysis=analysis,
                order=idx
            )
        
        # Trigger batch processing
        from .tasks import process_batch
        process_batch.delay(str(batch.id))
        
        return batch


class AnalysisBatchSerializer(serializers.ModelSerializer):
    """Serializer for AnalysisBatch with nested analyses"""
    analyses = serializers.SerializerMethodField()
    
    class Meta:
        model = AnalysisBatch
        fields = [
            'id', 'dataset', 'name', 'description', 'status',
            'total_analyses', 'completed_analyses', 'failed_analyses',
            'analyses', 'created_at', 'updated_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'status', 'total_analyses', 'completed_analyses',
            'failed_analyses', 'created_at', 'updated_at', 'completed_at'
        ]
    
    def get_analyses(self, obj):
        """Get all analyses in the batch"""
        batch_analyses = obj.batch_analyses.select_related('analysis', 'analysis__result').all()
        return [
            {
                'order': ba.order,
                'analysis': AnalysisSerializer(ba.analysis).data
            }
            for ba in batch_analyses
        ]


class ChartConfigOptionsSerializer(serializers.Serializer):
    """Serializer for available chart configuration options"""
    time_aggregations = serializers.ListField(child=serializers.CharField())
    aggregation_methods = serializers.ListField(child=serializers.CharField())
    chart_types = serializers.ListField(child=serializers.CharField())
    columns = serializers.ListField(child=serializers.CharField())
    numeric_columns = serializers.ListField(child=serializers.CharField())
    date_columns = serializers.ListField(child=serializers.CharField())