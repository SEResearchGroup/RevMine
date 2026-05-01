"""
Service Layer – Analysis Service
==================================
Thin orchestration service for analysis workflows. Coordinates between:
  - DatasetService   (load datasets from storage)
  - MetricsEngine    (compute charts and statistics)
  - Django ORM       (persist results)

No computation logic here — delegate everything to the domain layer.
"""
from __future__ import annotations

import logging

import pandas as pd
from django.utils import timezone

from analytics.models import AnalysisResult, MetricDefinition
from analytics.services.dataset_service import DatasetService
from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger(__name__)

# Date columns to parse when loading a dataset for analysis.
_DATE_COLUMNS = ["Creation_Date", "created_at", "updated_at", "merged_at", "closed_at"]


class AnalysisService:
    """
    Orchestrates the full analysis lifecycle:
      1. Load dataset from storage
      2. Pre-process dates
      3. Resolve the correct analysis function from MetricsEngine
      4. Execute the analysis
      5. Sanitize and persist the result

    Maintains backward compatibility: the ``function_mapping`` attribute
    is exposed so legacy code that accesses it directly continues to work.
    """

    DATE_COLUMNS = _DATE_COLUMNS

    def __init__(self) -> None:
        from analytics.domain.metrics.metrics_engine import MetricsEngine

        self._engine = MetricsEngine()
        # Expose function_mapping for backward compatibility.
        self.function_mapping = self._engine.function_mapping

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_analysis(self, analysis) -> None:
        """
        Run the full analysis pipeline and persist the result.

        Updates ``analysis.status`` to 'completed' or 'failed'.
        Raises on unexpected errors (caller may choose to swallow them).
        """
        try:
            analysis.status = "processing"
            analysis.save()

            df = DatasetService().load_dataframe(analysis.dataset)
            df = self._parse_dates(df)

            function_name = self._get_function_name(analysis.metric_code)
            analysis_fn = self._engine.function_mapping.get(function_name)

            if not analysis_fn:
                raise ValueError(
                    f"Analysis function for metric '{analysis.metric_code}' not found"
                )

            result_data = analysis_fn(df, analysis)
            result_data = self._engine._sanitize_value(result_data)

            AnalysisResult.objects.create(
                analysis=analysis,
                chart_data=result_data["chart_data"],
                chart_image=result_data.get("chart_image"),
                statistics=result_data.get("statistics"),
            )

            analysis.status = "completed"
            analysis.completed_at = timezone.now()
            analysis.save()

        except Exception as exc:
            analysis.status = "failed"
            analysis.error_message = str(exc)
            analysis.save()

    def _sanitize_value(self, value):
        """Proxy to MetricsEngine._sanitize_value for backward compatibility."""
        return self._engine._sanitize_value(value)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Parse well-known date columns in the DataFrame."""
        df_copy = df.copy()
        for col in self.DATE_COLUMNS:
            if col in df_copy.columns:
                df_copy[col] = pd.to_datetime(df_copy[col], errors="coerce", format="mixed")
        return df_copy

    def _get_function_name(self, metric_code: str) -> str:
        """
        Resolve the analysis function name for a metric code.

        Looks up MetricDefinition.analysis_function in the DB; falls back
        to the metric_code itself so custom/ad-hoc codes work without a DB
        entry.
        """
        try:
            metric = MetricDefinition.objects.get(code=metric_code)
            return metric.analysis_function
        except ObjectDoesNotExist:
            return metric_code
