"""
Analysis Service – Views
========================
Dynamic views for dataset management, metrics catalogue, and chart generation.

Endpoints summary
-----------------
Datasets
  GET  /datasets/                         → list datasets
  POST /datasets/upload/                  → upload a new dataset (CSV)
  GET  /datasets/<pk>/                    → dataset metadata
  DELETE /datasets/<pk>/                  → delete dataset
  GET  /datasets/<pk>/columns/            → column names + dtypes
  GET  /datasets/<pk>/preview/            → first N rows
  GET  /datasets/<pk>/available_metrics/  → metrics whose required_columns exist in dataset
  GET  /datasets/<pk>/compatible_axes/    → valid (x, y) pairs for custom charts

Metrics  (catalogue – read-only)
  GET  /metrics/                          → full catalogue
  GET  /metrics/categories/               → distinct category list
  GET  /metrics/by_category/              → metrics grouped by category
  GET  /metrics/<code>/                   → single metric detail

Generate
  POST /generate/                         → run analysis, return chart data + image

Analyses  (history)
  GET  /analyses/                         → list past analyses
  POST /analyses/bulk_create/             → create multiple analyses at once
  GET  /analyses/<pk>/                    → analysis metadata
  DELETE /analyses/<pk>/                  → delete analysis
  GET  /analyses/<pk>/result/             → chart_data + image of saved analysis
  POST /analyses/<pk>/retry/              → re-run analysis
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.utils import timezone

from analytics.models import Dataset, MetricDefinition, Analysis, AnalysisResult
from analytics.api.access import (
    filter_analysis_queryset_for_request,
    filter_dataset_queryset_for_request,
    get_analysis_for_request,
    get_dataset_for_request,
    get_request_user_id,
)
from analytics.services.dataset_service import DatasetService, DatasetStorageError
from analytics.services.analysis_service import AnalysisService
from analytics.api.serializers import (
    DatasetSerializer,
    DatasetUploadSerializer,
    MetricDefinitionSerializer,
    AnalysisSerializer,
    AnalysisListSerializer,
    AnalysisResultSerializer,
)


# ---------------------------------------------------------------------------
# Dataset views
# ---------------------------------------------------------------------------

class DatasetListView(APIView):
    """GET /datasets/ – list all datasets."""

    def get(self, request):
        workspace_id = request.query_params.get('workspace_id')
        repository_id = request.query_params.get('repository_id')
        source_type = request.query_params.get('source_type')

        queryset = filter_dataset_queryset_for_request(Dataset.objects.all(), request)

        if workspace_id:
            queryset = queryset.filter(workspace_id=workspace_id)
        if repository_id:
            queryset = queryset.filter(repository_id=repository_id)
        if source_type:
            queryset = queryset.filter(source_type=source_type)
        
        queryset = queryset.order_by('-uploaded_at')
        serializer = DatasetSerializer(queryset, many=True)
        
        return Response({
            "count": queryset.count(),
            "results": serializer.data
        })


class DatasetUploadView(APIView):
    """
    POST /datasets/upload/
    Body (multipart): file, workspace_id (optional), repository_id (optional), platform
    """
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = DatasetUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            dataset = serializer.save(user_id=get_request_user_id(request))
        except DatasetStorageError as exc:
            return Response(
                {
                    "error": "Dataset storage unavailable",
                    "detail": str(exc),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(DatasetSerializer(dataset).data, status=status.HTTP_201_CREATED)


class DatasetDetailView(APIView):
    """GET, DELETE /datasets/<pk>/"""

    def get(self, request, pk):
        dataset = get_dataset_for_request(request, pk)
        serializer = DatasetSerializer(dataset)
        return Response(serializer.data)

    def delete(self, request, pk):
        dataset = get_dataset_for_request(request, pk)
        service = DatasetService()
        service.delete_dataset(dataset)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DatasetColumnsView(APIView):
    """
    GET /datasets/<pk>/columns/
    Returns column names and inferred data-types.
    """

    def get(self, request, pk):
        dataset = get_dataset_for_request(request, pk)
        
        columns = []
        for col_name, meta in dataset.columns_metadata.items():
            columns.append({
                "name": col_name,
                "dtype": meta.get('type', 'unknown'),
                "nullable": meta.get('null_count', 0) > 0,
                "non_null_count": meta.get('non_null_count', 0),
                "null_count": meta.get('null_count', 0),
            })
        
        return Response({
            "dataset_id": str(pk),
            "columns": columns,
            "columns_metadata": dataset.columns_metadata
        })


class DatasetPreviewView(APIView):
    """
    GET /datasets/<pk>/preview/?rows=10
    Returns first N rows of the dataset.
    """

    def get(self, request, pk):
        dataset = get_dataset_for_request(request, pk)
        n = int(request.query_params.get("rows", 10))
        n = min(n, 100)  # Cap at 100 rows
        
        service = DatasetService()
        df = service.load_dataframe(dataset)
        
        # Convert to JSON-serializable format
        preview_data = df.head(n).to_dict('records')
        
        # Handle datetime serialization and NaN values
        import math
        for row in preview_data:
            for key, value in row.items():
                if hasattr(value, 'isoformat'):
                    row[key] = value.isoformat()
                elif isinstance(value, float) and math.isnan(value):
                    row[key] = None
        
        return Response({
            "dataset_id": str(pk),
            "rows": preview_data,
            "columns": list(df.columns),
            "total_rows": len(df),
            "preview_rows": len(preview_data)
        })


class DatasetAvailableMetricsView(APIView):
    """
    GET /datasets/<pk>/available_metrics/
    Returns metrics whose required_columns are all present in the dataset.
    """

    def get(self, request, pk):
        dataset = get_dataset_for_request(request, pk)
        service = DatasetService()
        
        result = service.get_available_metrics(dataset)
        available_columns = service.get_columns(dataset)
        
        return Response({
            "dataset_id": str(pk),
            "dataset_columns": available_columns,
            "count": len(result['available_metrics']),
            "metrics": MetricDefinitionSerializer(result['available_metrics'], many=True).data,
            "missing_columns_by_metric": result['missing_columns_by_metric']
        })


class DatasetCompatibleAxesView(APIView):
    """
    GET /datasets/<pk>/compatible_axes/
    Returns which columns are valid as X axis and which as Y axis
    so the frontend can build a meaningful custom chart selector.

    Rules:
      - X axis: datetime, categorical, or integer columns (for grouping)
      - Y axis: numeric columns (for aggregation)
    """

    def get(self, request, pk):
        dataset = get_dataset_for_request(request, pk)
        
        x_axis_options = []
        y_axis_options = []
        
        for col_name, meta in dataset.columns_metadata.items():
            col_type = meta.get('type', 'unknown')
            
            # X-axis: datetime, categorical, or can be used for grouping
            if col_type in ['datetime', 'datetime_string', 'categorical']:
                x_axis_options.append({
                    "column": col_name,
                    "dtype": col_type,
                    "label": col_name.replace('_', ' ').title(),
                })
            elif col_type == 'numeric':
                # Numeric columns with low unique values can be used for grouping
                unique_values = meta.get('unique_values', 0)
                if unique_values and unique_values < 50:
                    x_axis_options.append({
                        "column": col_name,
                        "dtype": "numeric_categorical",
                        "label": col_name.replace('_', ' ').title(),
                    })
            
            # Y-axis: numeric columns for aggregation
            if col_type == 'numeric':
                y_axis_options.append({
                    "column": col_name,
                    "dtype": "numeric",
                    "label": col_name.replace('_', ' ').title(),
                    "aggregations": ["sum", "mean", "median", "count", "min", "max"],
                    "min": meta.get('min'),
                    "max": meta.get('max'),
                    "mean": meta.get('mean'),
                })
        
        return Response({
            "dataset_id": str(pk),
            "x_axis": x_axis_options,
            "y_axis": y_axis_options,
            "time_aggregations": ["D", "W", "M", "Q", "Y"],
            "supported_chart_types": ["bar", "line", "scatter", "area", "pie"],
        })


# ---------------------------------------------------------------------------
# Metric views  (read-only catalogue)
# ---------------------------------------------------------------------------

class MetricListView(APIView):
    """GET /metrics/?source_type=code|kanban|cicd – full catalogue."""

    def get(self, request):
        metrics = MetricDefinition.objects.filter(is_active=True)
        source_type = request.query_params.get("source_type")
        if source_type:
            metrics = metrics.filter(source_type=source_type)
        serializer = MetricDefinitionSerializer(metrics, many=True)
        return Response({
            "count": metrics.count(),
            "metrics": serializer.data
        })


class MetricCategoriesView(APIView):
    """GET /metrics/categories/ – distinct categories."""

    def get(self, request):
        categories = (
            MetricDefinition.objects
            .filter(is_active=True)
            .values_list('category', flat=True)
            .distinct()
        )
        return Response({"categories": sorted(set(categories))})


class MetricByCategoryView(APIView):
    """
    GET /metrics/by_category/?category=timeseries
    Returns metrics grouped by category (or filtered if category param provided).
    """

    def get(self, request):
        category = request.query_params.get("category")
        source_type = request.query_params.get("source_type")

        metrics = MetricDefinition.objects.filter(is_active=True)
        if source_type:
            metrics = metrics.filter(source_type=source_type)

        if category:
            metrics = metrics.filter(category=category)
            serializer = MetricDefinitionSerializer(metrics, many=True)
            return Response({
                "category": category,
                "count": metrics.count(),
                "metrics": serializer.data
            })
        
        # Group by category
        by_category = {}
        for metric in metrics:
            if metric.category not in by_category:
                by_category[metric.category] = []
            by_category[metric.category].append(
                MetricDefinitionSerializer(metric).data
            )
        
        return Response(by_category)


class MetricDetailView(APIView):
    """GET /metrics/<code>/ – single metric."""

    def get(self, request, code):
        metric = get_object_or_404(MetricDefinition, code=code, is_active=True)
        serializer = MetricDefinitionSerializer(metric)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Generate  (core chart generation endpoint)
# ---------------------------------------------------------------------------

class GenerateChartView(APIView):
    """
    POST /generate/

    Accepts two modes:

    Mode A – Predefined metric
    --------------------------
    {
        "dataset_id": "<uuid>",
        "metric_code": "commits_over_time",
        "chart_type": "bar",              // optional, defaults to metric default
        "time_aggregation": "M",          // optional (D | W | M | Q | Y)
        "aggregation": "sum",             // optional
        "filters": {}                     // optional
    }

    Mode B – Custom axes
    --------------------
    {
        "dataset_id": "<uuid>",
        "x_axis": "Creation_Date",
        "y_axis": "#Commits",
        "aggregation": "sum",
        "chart_type": "line",
        "time_aggregation": "M",
        "filters": {}
    }

    Response (Chart.js / Recharts compatible)
    -----------------------------------------
    {
        "analysis_id": "<uuid>",
        "metric_code": "...",
        "chart_type": "...",
        "chart_data": { ... },            // Chart.js ready payload
        "image_base64": "...",            // matplotlib PNG as base64
        "statistics": {...},              // computed statistics
        "generated_at": "..."
    }
    """

    def post(self, request):
        dataset_id = request.data.get("dataset_id")
        metric_code = request.data.get("metric_code")
        x_axis = request.data.get("x_axis")
        y_axis = request.data.get("y_axis")
        chart_type = request.data.get("chart_type")
        aggregation = request.data.get("aggregation", "sum")
        time_aggregation = request.data.get("time_aggregation", "M")
        filters = request.data.get("filters", {})
        # Extra config dict passed from the frontend (e.g. time_filter for histograms)
        extra_config = request.data.get("config", {}) or {}

        # Validate dataset_id
        if not dataset_id:
            return Response(
                {"error": "'dataset_id' is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get dataset
        dataset = get_dataset_for_request(request, dataset_id)
        
        # Determine mode and validate
        if metric_code:
            # Mode A: Predefined metric
            metric = MetricDefinition.objects.filter(code=metric_code, is_active=True).first()
            if not metric:
                return Response(
                    {"error": f"Metric '{metric_code}' not found."},
                    status=status.HTTP_404_NOT_FOUND
                )
            chart_type = chart_type or metric.default_chart_type
            
            # Validate required columns exist
            service = DatasetService()
            available_columns = set(service.get_columns(dataset))
            missing_columns = set(metric.required_columns) - available_columns
            
            if missing_columns:
                return Response(
                    {
                        "error": f"Dataset is missing required columns for metric '{metric_code}'.",
                        "missing_columns": list(missing_columns)
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        elif x_axis and y_axis:
            # Mode B: Custom axes
            metric_code = "custom_chart"
            chart_type = chart_type or "bar"
            
            # Validate columns exist
            service = DatasetService()
            available_columns = set(service.get_columns(dataset))
            
            if x_axis not in available_columns:
                return Response(
                    {"error": f"X-axis column '{x_axis}' not found in dataset."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if y_axis not in available_columns:
                return Response(
                    {"error": f"Y-axis column '{y_axis}' not found in dataset."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response(
                {"error": "Provide either 'metric_code' or both 'x_axis' and 'y_axis'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create Analysis record – only include x_axis / y_axis when they
        # are explicitly provided so that analysis functions fall back to
        # their own defaults via config.get('x_axis', '<default>').
        config = {
            "time_aggregation": time_aggregation,
            "aggregation": aggregation,
            "filters": filters,
        }
        # Merge any extra config keys (e.g. time_filter for histogram metrics)
        for key, value in extra_config.items():
            if key not in config:
                config[key] = value
        if x_axis is not None:
            config["x_axis"] = x_axis
        if y_axis is not None:
            config["y_axis"] = y_axis
        
        analysis = Analysis.objects.create(
            dataset=dataset,
            metric_code=metric_code,
            chart_type=chart_type,
            config=config,
            status='pending'
        )

        try:
            # Process analysis synchronously for immediate response
            analysis_service = AnalysisService()
            analysis_service.process_analysis(analysis)
            
            # Refresh from DB to get result
            analysis.refresh_from_db()
            
            if analysis.status != 'completed':
                return Response(
                    {
                        "error": "Analysis failed.",
                        "message": analysis.error_message,
                        "analysis_id": str(analysis.id)
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Get result
            result = analysis.result
            
            return Response(
                {
                    "analysis_id": str(analysis.id),
                    "dataset_id": str(dataset_id),
                    "metric_code": metric_code,
                    "chart_type": chart_type,
                    "x_axis": x_axis or config.get('x_axis'),
                    "y_axis": y_axis or config.get('y_axis'),
                    "aggregation": aggregation,
                    "time_aggregation": time_aggregation,
                    "chart_data": result.chart_data,
                    "image_base64": result.chart_image,
                    "statistics": result.statistics,
                    "generated_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
                },
                status=status.HTTP_201_CREATED,
            )
            
        except Exception as e:
            return Response(
                {
                    "error": "Analysis processing failed.",
                    "message": str(e),
                    "analysis_id": str(analysis.id)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ---------------------------------------------------------------------------
# Analysis views  (history)
# ---------------------------------------------------------------------------

class AnalysisListView(APIView):
    """GET /analyses/ – list past analyses."""

    def get(self, request):
        dataset_id = request.query_params.get('dataset_id')
        status_filter = request.query_params.get('status')
        metric_code = request.query_params.get('metric_code')
        
        queryset = filter_analysis_queryset_for_request(
            Analysis.objects.select_related('dataset').prefetch_related('result'),
            request,
        )
        
        if dataset_id:
            queryset = queryset.filter(dataset_id=dataset_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if metric_code:
            queryset = queryset.filter(metric_code=metric_code)
        
        queryset = queryset.order_by('-created_at')
        serializer = AnalysisListSerializer(queryset, many=True)
        
        return Response({
            "count": queryset.count(),
            "results": serializer.data
        })


class AnalysisBulkCreateView(APIView):
    """
    POST /analyses/bulk_create/
    Body: {
        "dataset_id": "<uuid>",
        "analyses": [
            {"metric_code": "commits_over_time", "chart_type": "line", "config": {...}},
            {"metric_code": "lead_time_distribution", "chart_type": "histogram"},
            ...
        ]
    }
    Creates multiple analyses and processes them.
    """

    def post(self, request):
        dataset_id = request.data.get("dataset_id")
        analyses_data = request.data.get("analyses", [])

        if not dataset_id:
            return Response(
                {"error": "'dataset_id' is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not analyses_data:
            return Response(
                {"error": "'analyses' array is required and cannot be empty."},
                status=status.HTTP_400_BAD_REQUEST
            )

        dataset = get_dataset_for_request(request, dataset_id)
        
        created_analyses = []
        errors = []
        
        for idx, analysis_data in enumerate(analyses_data):
            metric_code = analysis_data.get('metric_code')
            chart_type = analysis_data.get('chart_type')
            config = analysis_data.get('config', {})
            
            if not metric_code:
                errors.append({
                    "index": idx,
                    "error": "'metric_code' is required."
                })
                continue
            
            # Validate metric exists
            metric = MetricDefinition.objects.filter(code=metric_code, is_active=True).first()
            if not metric:
                errors.append({
                    "index": idx,
                    "error": f"Metric '{metric_code}' not found."
                })
                continue
            
            chart_type = chart_type or metric.default_chart_type
            
            # Create analysis
            analysis = Analysis.objects.create(
                dataset=dataset,
                metric_code=metric_code,
                chart_type=chart_type,
                config=config,
                status='pending'
            )
            
            # Process analysis
            try:
                analysis_service = AnalysisService()
                analysis_service.process_analysis(analysis)
                analysis.refresh_from_db()
            except Exception as e:
                analysis.status = 'failed'
                analysis.error_message = str(e)
                analysis.save()
            
            created_analyses.append(analysis)

        return Response(
            {
                "created": len(created_analyses),
                "analyses": AnalysisSerializer(created_analyses, many=True).data,
                "errors": errors if errors else None
            },
            status=status.HTTP_201_CREATED,
        )


class AnalysisDetailView(APIView):
    """GET, DELETE /analyses/<pk>/ – analysis metadata."""

    def get(self, request, pk):
        analysis = get_object_or_404(
            filter_analysis_queryset_for_request(
                Analysis.objects.select_related('dataset').prefetch_related('result'),
                request,
            ),
            pk=pk,
        )
        serializer = AnalysisSerializer(analysis)
        return Response(serializer.data)

    def delete(self, request, pk):
        analysis = get_analysis_for_request(request, pk)
        analysis.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AnalysisResultView(APIView):
    """
    GET /analyses/<pk>/result/
    Returns the saved chart_data + image of a completed analysis.
    """

    def get(self, request, pk):
        analysis = get_object_or_404(
            filter_analysis_queryset_for_request(
                Analysis.objects.select_related('dataset').prefetch_related('result'),
                request,
            ),
            pk=pk,
        )
        
        if analysis.status == 'pending':
            return Response(
                {"error": "Analysis is still pending.", "status": analysis.status},
                status=status.HTTP_202_ACCEPTED
            )
        
        if analysis.status == 'processing':
            return Response(
                {"error": "Analysis is currently processing.", "status": analysis.status},
                status=status.HTTP_202_ACCEPTED
            )
        
        if analysis.status == 'failed':
            return Response(
                {
                    "error": "Analysis failed.",
                    "status": analysis.status,
                    "message": analysis.error_message
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not hasattr(analysis, 'result') or analysis.result is None:
            return Response(
                {"error": "Analysis result not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        result = analysis.result
        
        return Response({
            "analysis_id": str(analysis.id),
            "dataset_id": str(analysis.dataset_id),
            "metric_code": analysis.metric_code,
            "chart_type": analysis.chart_type,
            "config": analysis.config,
            "status": analysis.status,
            "chart_data": result.chart_data,
            "image_base64": result.chart_image,
            "statistics": result.statistics,
            "generated_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
        })


class AnalysisRetryView(APIView):
    """
    POST /analyses/<pk>/retry/
    Re-runs the analysis (e.g. after a dataset update or a previous failure).
    """

    def post(self, request, pk):
        analysis = get_analysis_for_request(request, pk)
        
        if analysis.status not in ['failed', 'completed']:
            return Response(
                {"error": "Only failed or completed analyses can be retried."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reset status
        analysis.status = 'pending'
        analysis.error_message = None
        analysis.completed_at = None
        analysis.save()
        
        # Delete old result if exists
        if hasattr(analysis, 'result') and analysis.result:
            analysis.result.delete()
        
        try:
            # Process analysis
            analysis_service = AnalysisService()
            analysis_service.process_analysis(analysis)
            analysis.refresh_from_db()
            
            if analysis.status == 'completed':
                result = analysis.result
                return Response({
                    "analysis_id": str(analysis.id),
                    "status": analysis.status,
                    "message": "Analysis has been re-executed successfully.",
                    "chart_data": result.chart_data,
                    "image_base64": result.chart_image,
                    "statistics": result.statistics,
                    "generated_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
                })
            else:
                return Response({
                    "analysis_id": str(analysis.id),
                    "status": analysis.status,
                    "message": "Analysis retry failed.",
                    "error": analysis.error_message
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            return Response({
                "analysis_id": str(analysis.id),
                "status": "failed",
                "message": "Analysis retry failed.",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ---------------------------------------------------------------------------
# Analysis history  (grouped by dataset for the panel page)
# ---------------------------------------------------------------------------

class AnalysisHistoryView(APIView):
    """
    GET /analyses/history/
    Returns analysis history grouped by dataset, for the history panel page.
    Each dataset entry includes: dataset info, count of analyses, dates, statuses.
    """

    def get(self, request):
        workspace_id = request.query_params.get('workspace_id')
        
        datasets_qs = filter_dataset_queryset_for_request(
            Dataset.objects.prefetch_related('analyses').all(),
            request,
        )
        
        if workspace_id:
            datasets_qs = datasets_qs.filter(workspace_id=workspace_id)
        
        # Only datasets that have at least one analysis
        datasets_with_analyses = []
        for dataset in datasets_qs:
            analyses = dataset.analyses.all()
            if not analyses.exists():
                continue
            
            completed = analyses.filter(status='completed').count()
            failed = analyses.filter(status='failed').count()
            total = analyses.count()
            
            # Get date range from analyses
            first_analysis = analyses.order_by('created_at').first()
            last_analysis = analyses.order_by('-created_at').first()
            
            # Get unique metric codes used
            metric_codes = list(analyses.values_list('metric_code', flat=True).distinct())
            
            datasets_with_analyses.append({
                'dataset': DatasetSerializer(dataset).data,
                'analysis_summary': {
                    'total_analyses': total,
                    'completed': completed,
                    'failed': failed,
                    'pending': total - completed - failed,
                    'metric_codes': metric_codes,
                    'first_analysis_date': first_analysis.created_at.isoformat() if first_analysis else None,
                    'last_analysis_date': last_analysis.created_at.isoformat() if last_analysis else None,
                }
            })
        
        # Sort by last analysis date descending
        datasets_with_analyses.sort(
            key=lambda x: x['analysis_summary']['last_analysis_date'] or '',
            reverse=True
        )
        
        return Response({
            'count': len(datasets_with_analyses),
            'results': datasets_with_analyses
        })


class DatasetSummaryView(APIView):
    """
    GET /datasets/<pk>/summary/
    Returns a comprehensive summary of the dataset for dashboard display:
    total rows, date range, column stats, key metrics computed from the raw data.
    """

    def get(self, request, pk):
        dataset = get_dataset_for_request(request, pk)
        
        service = DatasetService()
        try:
            df = service.load_dataframe(dataset)
        except Exception as e:
            return Response(
                {"error": f"Failed to load dataset: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        summary = {
            'dataset_id': str(pk),
            'filename': dataset.filename,
            'total_rows': dataset.rows_count,
            'total_columns': dataset.columns_count,
            'uploaded_at': dataset.uploaded_at.isoformat() if dataset.uploaded_at else None,
        }
        
        # Date range from Creation_Date if available
        if 'Creation_Date' in df.columns:
            import pandas as pd
            dates = pd.to_datetime(df['Creation_Date'], errors='coerce').dropna()
            if len(dates) > 0:
                summary['date_range'] = {
                    'start': dates.min().isoformat(),
                    'end': dates.max().isoformat(),
                }
        
        # MR/PR counts
        summary['total_mrs'] = len(df)
        
        # State distribution if available
        if 'state' in df.columns:
            state_counts = df['state'].value_counts().to_dict()
            summary['state_distribution'] = {str(k): int(v) for k, v in state_counts.items()}
        
        # Key numeric column averages
        import pandas as pd
        numeric_summaries = {}
        key_cols = [
            '#Commits', '#Discussions', '#UniqueCommiters', 'modified_files',
            'comments', '#people', '#reviewers', 'Lead_Time',
            'additions', 'deletions', 'churn_addition', 'churn_deletions',
            'initial_mr_size', 'rework_size', 'hist_entropy',
        ]
        for col in key_cols:
            if col in df.columns:
                vals = pd.to_numeric(df[col], errors='coerce').dropna()
                if len(vals) > 0:
                    numeric_summaries[col] = {
                        'mean': round(float(vals.mean()), 2),
                        'median': round(float(vals.median()), 2),
                        'min': float(vals.min()),
                        'max': float(vals.max()),
                        'sum': float(vals.sum()),
                    }
        
        summary['numeric_summaries'] = numeric_summaries
        
        # Platform info
        summary['platform'] = dataset.platform
        summary['workspace_id'] = dataset.workspace_id
        summary['repository_id'] = dataset.repository_id

        return Response(summary)


class AutomationPreviewView(APIView):
    """
    POST /automation/preview/

    "AI Prompt" mode of MetricsSelectionPage.jsx.

    Receives a natural-language prompt and maps it to existing metric_code values
    via the LLM Service intent-parsing endpoint (the legacy 'analyze' flow).
    This is DISTINCT from the DSL-First pipeline: the LLM here does NOT generate
    a DSL document — it maps NL to catalogue metric codes.

    Request body:
    {
        "dataset_id":   "<uuid>",
        "prompt":       "Show commits over time for Alice",
        "llm_provider": "openrouter" | "ollama",
        "model":        "openai/gpt-4o-mini"   // optional
    }

    Response (200):
    {
        "prompt":    "Show commits over time for Alice",
        "analyses":  [{"metric_code": "commits_over_time", "chart_type": "line", "config": {}}],
        "selection": {
            "metrics":       ["commits_over_time"],
            "visualization": "line_chart",
            "chart_type":    "line",
            "filters":       {"date_range": null, "authors": ["Alice"], "repositories": []}
        },
        "warnings":  []
    }
    """

    # Map LLM visualization label → chart_type string consumed by /generate/
    _VIZ_TO_CHART = {
        "line_chart":   "line",
        "bar_chart":    "bar",
        "pie_chart":    "pie",
        "scatter_plot": "scatter",
        "histogram":    "histogram",
        "area_chart":   "area",
        "heatmap":      "heatmap",
    }

    def post(self, request):
        import requests as http_requests
        from django.conf import settings

        dataset_id  = request.data.get("dataset_id")
        prompt      = (request.data.get("prompt") or "").strip()
        llm_provider = request.data.get("llm_provider", "openrouter")
        model       = request.data.get("model")

        if not dataset_id:
            return Response({"error": "'dataset_id' is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not prompt:
            return Response({"error": "'prompt' is required."}, status=status.HTTP_400_BAD_REQUEST)

        dataset = get_dataset_for_request(request, dataset_id)

        # ── 1. Get available metric codes for this dataset ──────────────────
        from analytics.services.dataset_service import DatasetService
        svc = DatasetService()
        metrics_result = svc.get_available_metrics(dataset)
        available_codes = {m.code for m in metrics_result["available_metrics"]}
        code_to_metric  = {m.code: m for m in metrics_result["available_metrics"]}

        # ── 2. Call LLM Service (intent-parsing prompt) ─────────────────────
        llm_base = getattr(settings, "LLM_SERVICE_URL", "http://llm-service:8004")
        endpoint = f"{llm_base}/openrouter" if llm_provider == "openrouter" else f"{llm_base}/ollama"

        llm_payload = {"user_message": prompt}
        if model:
            llm_payload["model"] = model

        try:
            resp = http_requests.post(endpoint, json=llm_payload, timeout=60)
            resp.raise_for_status()
            llm_data = resp.json()
        except http_requests.exceptions.ConnectionError:
            return Response(
                {"error": f"LLM service unreachable at {llm_base}. Is the llm-service container running?"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except http_requests.exceptions.HTTPError as exc:
            return Response(
                {"error": f"LLM service error: {exc.response.text}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # ── 3. Parse LLM intent response ─────────────────────────────────────
        # LLM service wraps the result: {"model": "...", "result": {...}}
        intent_result = llm_data.get("result") or llm_data

        requested_metrics  = intent_result.get("metrics", [])
        llm_filters        = intent_result.get("filters") or {}
        llm_visualization  = intent_result.get("visualization", "")
        chart_type         = self._VIZ_TO_CHART.get(llm_visualization, "bar")

        # ── 4. Resolve metric codes to analyses ───────────────────────────────
        warnings  = []
        analyses  = []

        for code in requested_metrics:
            if code not in available_codes:
                warnings.append(
                    f"Metric '{code}' is not available for this dataset "
                    "(missing required columns or not in catalogue)."
                )
                continue

            metric_obj = code_to_metric[code]
            # Use LLM-suggested chart type, but fall back to the metric's default
            resolved_chart = chart_type or metric_obj.default_chart_type or "bar"
            config = {}

            # Propagate LLM filters into config if the metric supports them
            if llm_filters.get("date_range"):
                config["date_range"] = llm_filters["date_range"]
            if llm_filters.get("authors"):
                config["authors"] = llm_filters["authors"]

            analyses.append({
                "metric_code": code,
                "chart_type":  resolved_chart,
                "config":      config,
            })

        if not analyses and requested_metrics:
            warnings.insert(0, "None of the LLM-suggested metrics are available for this dataset.")

        return Response({
            "prompt":    prompt,
            "analyses":  analyses,
            "selection": {
                "metrics":       [a["metric_code"] for a in analyses],
                "visualization": llm_visualization,
                "chart_type":    chart_type,
                "filters":       llm_filters,
            },
            "warnings": warnings,
        })


# ---------------------------------------------------------------------------
# Custom DSL analysis views  (DSL-First pipeline)
# ---------------------------------------------------------------------------

class CustomAnalysisView(APIView):
    """
    POST /custom/

    Accepts a natural-language query (or a raw DSL document) and returns
    a fully executed chart + statistics without requiring the user to know
    any metric code.

    Body (NL mode):
    {
        "dataset_id":   "<uuid>",
        "nl_query":     "Show average lead time by author",
        "model":        "openai/gpt-4o-mini",   // optional
        "backend":      "openrouter",            // optional: openrouter | ollama
        "custom_label": "My custom chart"        // optional
    }

    Body (DSL mode – skips LLM):
    {
        "dataset_id": "<uuid>",
        "dsl": { "version": "1", "source": {...}, ... }
    }

    Response:
    {
        "status":       "completed" | "dsl_error",
        "analysis_id":  "<uuid>",
        "dsl":          { ... },       // the DSL document used
        "chart_type":   "bar",
        "chart_data":   { ... },
        "chart_image":  "data:image/png;base64,...",
        "statistics":   { ... },
        "generated_at": "ISO-8601"
    }
    """

    def post(self, request):
        from analytics.services.custom_analysis_service import CustomAnalysisService

        dataset_id = request.data.get("dataset_id")
        nl_query = request.data.get("nl_query", "").strip()
        dsl_raw = request.data.get("dsl")
        model = request.data.get("model")
        backend = request.data.get("backend", "openrouter")
        custom_label = request.data.get("custom_label")

        if not dataset_id:
            return Response(
                {"error": "'dataset_id' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not nl_query and not dsl_raw:
            return Response(
                {"error": "Provide either 'nl_query' or 'dsl'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dataset = get_dataset_for_request(request, dataset_id)
        service = CustomAnalysisService()

        try:
            if dsl_raw:
                result = service.run_from_dsl(
                    dataset=dataset,
                    dsl_raw=dsl_raw,
                    nl_query=nl_query or None,
                    custom_label=custom_label,
                )
            else:
                result = service.run_from_nl_query(
                    dataset=dataset,
                    nl_query=nl_query,
                    model=model,
                    backend=backend,
                    custom_label=custom_label,
                )
        except RuntimeError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as exc:
            return Response(
                {"error": f"Custom analysis failed: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if result.get("status") == "dsl_error":
            return Response(result, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        return Response(result, status=status.HTTP_201_CREATED)


class CustomAnalysisHistoryView(APIView):
    """
    GET /custom/history/?dataset_id=<uuid>&workspace_id=<int>

    Returns saved custom analyses for the current user/workspace,
    ordered by most recent first.
    """

    def get(self, request):
        dataset_id = request.query_params.get("dataset_id")
        workspace_id = request.query_params.get("workspace_id")

        queryset = filter_analysis_queryset_for_request(
            Analysis.objects.filter(is_custom=True)
                .select_related("dataset")
                .prefetch_related("result"),
            request,
        ).order_by("-created_at")

        if dataset_id:
            queryset = queryset.filter(dataset_id=dataset_id)
        if workspace_id:
            queryset = queryset.filter(dataset__workspace_id=workspace_id)

        results = []
        for analysis in queryset[:50]:  # cap at 50
            entry = {
                "analysis_id": str(analysis.id),
                "dataset_id": str(analysis.dataset_id),
                "dataset_name": analysis.dataset.filename if analysis.dataset else "",
                "nl_query": analysis.nl_query or "",
                "custom_label": analysis.custom_label or "",
                "chart_type": analysis.chart_type,
                "dsl": analysis.dsl_config,
                "status": analysis.status,
                "created_at": analysis.created_at.isoformat(),
                "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
            }
            if hasattr(analysis, "result") and analysis.result:
                entry["chart_data"] = analysis.result.chart_data
                entry["statistics"] = analysis.result.statistics
            results.append(entry)

        return Response({"count": len(results), "results": results})


class CustomAnalysisValidateView(APIView):
    """
    POST /custom/validate/

    Validate a DSL document against a dataset's columns without executing it.
    Useful for the frontend to give immediate feedback before running.

    Body: { "dataset_id": "<uuid>", "dsl": { ... } }

    Response:
    {
        "valid": true | false,
        "errors": ["..."],
        "dsl": { ... }  // echo back on success
    }
    """

    def post(self, request):
        from analytics.domain.dsl.validator import DSLValidator

        dataset_id = request.data.get("dataset_id")
        dsl_raw = request.data.get("dsl", {})

        if not dataset_id:
            return Response({"error": "'dataset_id' is required."}, status=status.HTTP_400_BAD_REQUEST)

        dataset = get_dataset_for_request(request, dataset_id)
        columns_metadata = dataset.columns_metadata or {}

        validator = DSLValidator(available_columns=columns_metadata)
        errors = validator.validate_only(dsl_raw)

        if errors:
            return Response({"valid": False, "errors": errors})
        return Response({"valid": True, "dsl": dsl_raw})


class SmartPreviewView(APIView):
    """
    POST /automation/smart-preview/

    Unified AI analysis preview (no execution):
    1. Try predefined metrics via intent-parsing (AutomationPreviewView logic).
    2. If no predefined analyses resolved → generate DSL only (no execute).
    3. If DSL is insufficient → generate Python code.

    Response:
    {
        "mode":      "predefined" | "custom_dsl" | "python_code" | "dsl_error",
        // predefined:
        "analyses":  [...],
        "selection": {...},
        "warnings":  [...],
        // custom_dsl:
        "dsl_raw":   {...},
        "dsl_plan":  { "metric": "...", "aggregation": "avg", "group_by": {...}, ... },
        // python_code:
        "code":      "python code string",
        "reason":    "why DSL was insufficient",
        // dsl_error:
        "error":     "...",
    }
    """

    _VIZ_TO_CHART = {
        "line_chart":   "line",
        "bar_chart":    "bar",
        "pie_chart":    "pie",
        "scatter_plot": "scatter",
        "histogram":    "histogram",
        "area_chart":   "area",
        "heatmap":      "heatmap",
    }

    def post(self, request):
        import requests as http_requests
        from django.conf import settings
        from analytics.services.custom_analysis_service import CustomAnalysisService
        from analytics.services.dataset_service import DatasetService

        dataset_id   = request.data.get("dataset_id")
        prompt       = (request.data.get("prompt") or "").strip()
        llm_provider = request.data.get("llm_provider", "openrouter")
        model        = request.data.get("model")

        if not dataset_id:
            return Response({"error": "'dataset_id' is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not prompt:
            return Response({"error": "'prompt' is required."}, status=status.HTTP_400_BAD_REQUEST)

        dataset = get_dataset_for_request(request, dataset_id)

        # ── 1. Try predefined metrics ────────────────────────────────────
        svc = DatasetService()
        metrics_result   = svc.get_available_metrics(dataset)
        available_codes  = {m.code for m in metrics_result["available_metrics"]}
        code_to_metric   = {m.code: m for m in metrics_result["available_metrics"]}

        llm_base = getattr(settings, "LLM_SERVICE_URL", "http://llm-service:8004")
        intent_endpoint  = f"{llm_base}/openrouter" if llm_provider == "openrouter" else f"{llm_base}/ollama"

        llm_payload = {"user_message": prompt}
        if model:
            llm_payload["model"] = model

        predefined_analyses = []
        predefined_warnings = []
        predefined_selection = {}

        try:
            resp = http_requests.post(intent_endpoint, json=llm_payload, timeout=60)
            resp.raise_for_status()
            llm_data = resp.json()
            intent_result = llm_data.get("result") or llm_data

            requested_metrics = intent_result.get("metrics", [])
            llm_filters       = intent_result.get("filters") or {}
            llm_visualization = intent_result.get("visualization", "")
            chart_type        = self._VIZ_TO_CHART.get(llm_visualization, "bar")

            for code in requested_metrics:
                if code not in available_codes:
                    predefined_warnings.append(
                        f"Metric '{code}' is not available for this dataset."
                    )
                    continue
                metric_obj     = code_to_metric[code]
                resolved_chart = chart_type or metric_obj.default_chart_type or "bar"
                config = {}
                if llm_filters.get("date_range"):
                    config["date_range"] = llm_filters["date_range"]
                if llm_filters.get("authors"):
                    config["authors"] = llm_filters["authors"]
                predefined_analyses.append({
                    "metric_code": code,
                    "chart_type":  resolved_chart,
                    "config":      config,
                })

            predefined_selection = {
                "metrics":       [a["metric_code"] for a in predefined_analyses],
                "visualization": llm_visualization,
                "chart_type":    chart_type,
                "filters":       llm_filters,
            }

        except (http_requests.exceptions.ConnectionError, http_requests.exceptions.HTTPError):
            # LLM service unreachable — skip predefined, go straight to DSL
            pass

        # If predefined metrics found → return immediately
        if predefined_analyses:
            return Response({
                "mode":      "predefined",
                "analyses":  predefined_analyses,
                "selection": predefined_selection,
                "warnings":  predefined_warnings,
            })

        # ── 2. No predefined match → try DSL generation ─────────────────
        custom_svc = CustomAnalysisService()
        try:
            preview = custom_svc.preview_nl_query(
                dataset=dataset,
                nl_query=prompt,
                model=model,
                backend=llm_provider,
            )
        except RuntimeError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(preview)


class PythonAnalysisView(APIView):
    """
    POST /custom/python/

    Execute a Python code snippet on the dataset.

    Body:
    {
        "dataset_id":   "<uuid>",
        "code":         "result_data = [...]; chart_type = 'bar'",
        "nl_query":     "...",       // optional, for history
        "custom_label": "..."        // optional
    }

    Or generate code from NL and execute in one shot:
    {
        "dataset_id":  "<uuid>",
        "nl_query":    "Defect rate per author",
        "generate":    true,
        "backend":     "openrouter",
        "model":       "openai/gpt-4o-mini"
    }
    """

    def post(self, request):
        from analytics.services.custom_analysis_service import CustomAnalysisService

        dataset_id   = request.data.get("dataset_id")
        code         = request.data.get("code", "").strip()
        nl_query     = (request.data.get("nl_query") or "").strip()
        custom_label = request.data.get("custom_label")
        generate     = request.data.get("generate", False)
        model        = request.data.get("model")
        backend      = request.data.get("backend", "openrouter")

        if not dataset_id:
            return Response({"error": "'dataset_id' is required."}, status=status.HTTP_400_BAD_REQUEST)

        dataset = get_dataset_for_request(request, dataset_id)
        service = CustomAnalysisService()

        # Auto-generate code from NL if requested
        if generate and nl_query and not code:
            columns_metadata = dataset.columns_metadata or {}
            column_names = list(columns_metadata.keys())
            try:
                code = service._generate_python_code(
                    nl_query, column_names, model=model, backend=backend
                )
            except RuntimeError as exc:
                return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        if not code:
            return Response(
                {"error": "Provide either 'code' or set 'generate': true with 'nl_query'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = service.run_python_analysis(
                dataset=dataset,
                python_code=code,
                nl_query=nl_query or None,
                custom_label=custom_label,
            )
        except Exception as exc:
            return Response(
                {"error": f"Python analysis failed: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if result.get("status") == "python_error":
            return Response(result, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        return Response(result, status=status.HTTP_201_CREATED)
