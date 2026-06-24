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
from analytics.domain.analysis.custom_formula import CUSTOM_FORMULA_METRIC_CODE
from analytics.api.access import (
    filter_analysis_queryset_for_request,
    filter_dataset_queryset_for_request,
    get_analysis_for_request,
    get_dataset_for_request,
    get_request_user_id,
)
from analytics.services.dataset_service import DatasetService, DatasetStorageError
from analytics.services.analysis_service import AnalysisService
from analytics.services.custom_analysis_service import (
    CustomAnalysisServiceError,
    CustomAnalysisSuggestionService,
    CustomAnalysisValidationError,
)
from analytics.services.personalized_analysis_service import (
    PersonalizedAnalysisError,
    PersonalizedAnalysisService,
)
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


class CustomAnalysisPreviewView(APIView):
    """
    POST /custom_analyses/preview/
    Turns a natural-language custom analysis request into a reviewable formula.
    """

    def post(self, request):
        dataset_id = request.data.get("dataset_id")
        if not dataset_id:
            return Response(
                {"error": "'dataset_id' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dataset = get_dataset_for_request(request, dataset_id)

        try:
            preview = CustomAnalysisSuggestionService.generate_preview(
                dataset=dataset,
                payload=request.data,
            )
        except CustomAnalysisValidationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except CustomAnalysisServiceError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(preview, status=status.HTTP_200_OK)


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
        if metric_code and metric_code != CUSTOM_FORMULA_METRIC_CODE:
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
        elif metric_code == CUSTOM_FORMULA_METRIC_CODE:
            chart_type = chart_type or extra_config.get("chart_type") or "bar"
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
        # Merge any extra config keys (formula, time_filter, etc.). Explicit
        # top-level axis params are applied below and keep precedence.
        for key, value in extra_config.items():
            if value is not None:
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
            response_config = analysis.config or {}
            
            return Response(
                {
                    "analysis_id": str(analysis.id),
                    "dataset_id": str(dataset_id),
                    "metric_code": metric_code,
                    "chart_type": chart_type,
                    "x_axis": response_config.get('x_axis'),
                    "y_axis": response_config.get('y_axis'),
                    "aggregation": response_config.get("aggregation"),
                    "time_aggregation": response_config.get("time_aggregation"),
                    "config": response_config,
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
            
            # Validate metric exists unless this is an ad-hoc formula analysis.
            if metric_code == CUSTOM_FORMULA_METRIC_CODE:
                chart_type = chart_type or config.get("chart_type") or "bar"
            else:
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
                    "dataset_id": str(analysis.dataset_id),
                    "metric_code": analysis.metric_code,
                    "chart_type": analysis.chart_type,
                    "config": analysis.config,
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


class PersonalizedAnalysisView(APIView):
    """
    POST /personalized_analyses/

    End-to-end natural-language → chart pipeline.

    Request body
    ------------
    {
        "dataset_id": "<uuid>",
        "prompt":     "La moyenne de changements par auteur",
        "provider":   "openrouter",          // optional, default "openrouter"
        "model":      "anthropic/claude-sonnet-4-6"  // optional
    }

    Response
    --------
    {
        "analysis_id":  "<uuid>",
        "dataset_id":   "<uuid>",
        "scenario":     "csv_existing" | "csv_derived" | "raw_json",
        "plan": {
            "name":              "...",
            "formula":           "...",
            "output_column":     "...",
            "explanation":       "...",
            "aggregation_scope": "...",
            "aggregation":       "...",
            "chart_type":        "...",
            "x_axis":            "..."
        },
        "chart_data":   {...},
        "image_base64": "...",
        "statistics":   {...},
        "warnings":     [],
        "generated_at": "ISO timestamp"
    }
    """

    def post(self, request):
        dataset_id = request.data.get("dataset_id")
        prompt = str(request.data.get("prompt") or "").strip()

        if not dataset_id:
            return Response(
                {"error": "'dataset_id' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not prompt:
            return Response(
                {"error": "'prompt' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dataset = get_dataset_for_request(request, dataset_id)

        llm_provider = str(request.data.get("provider") or "openrouter").strip()
        model = request.data.get("model") or "anthropic/claude-sonnet-4-6"

        try:
            result = PersonalizedAnalysisService().execute(
                dataset=dataset,
                prompt=prompt,
                llm_provider=llm_provider,
                model=model,
            )
        except PersonalizedAnalysisError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        return Response(
            {
                "analysis_id": result.analysis_id,
                "dataset_id": result.dataset_id,
                "scenario": result.plan.scenario,
                "plan": {
                    "name": result.plan.name,
                    "formula": result.plan.formula,
                    "output_column": result.output_column,
                    "explanation": result.plan.explanation,
                    "aggregation_scope": result.plan.aggregation_scope,
                    "aggregation": result.plan.aggregation,
                    "chart_type": result.plan.chart_type,
                    "x_axis": result.plan.x_axis,
                },
                "chart_data": result.chart_data,
                "image_base64": result.chart_image,
                "statistics": result.statistics,
                "warnings": result.warnings,
            },
            status=status.HTTP_201_CREATED,
        )


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
