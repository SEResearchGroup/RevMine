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
import time

import pandas as pd
from django.utils import timezone

from analytics.models import AnalysisResult, MetricDefinition
from analytics.services.dataset_service import DatasetService
from analytics.domain.analysis.custom_formula import (
    CUSTOM_FORMULA_METRIC_CODE,
    evaluate_formula,
    slugify_output_column,
)
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
        _start = time.monotonic()
        dataset_id = str(getattr(analysis, "dataset_id", ""))
        metric_code = getattr(analysis, "metric_code", "unknown")

        try:
            analysis.status = "processing"
            analysis.save()

            logger.info(
                "Analysis pipeline started",
                extra={
                    "analysis_id": str(analysis.id),
                    "metric": metric_code,
                    "dataset_id": dataset_id,
                    "status": "processing",
                    "event": "analysis_started",
                },
            )

            _load_start = time.monotonic()
            dataset_service = DatasetService()
            df = dataset_service.load_dataframe(analysis.dataset)
            df = self._parse_dates(df)
            df = self._apply_custom_formula_if_needed(df, analysis, dataset_service)
            _load_duration = round(time.monotonic() - _load_start, 3)

            logger.info(
                "Dataset loaded for analysis",
                extra={
                    "analysis_id": str(analysis.id),
                    "dataset_id": dataset_id,
                    "rows": len(df),
                    "columns": list(df.columns),
                    "load_duration": _load_duration,
                    "event": "analysis_dataset_loaded",
                },
            )

            function_name = self._get_function_name(analysis.metric_code)
            analysis_fn = self._engine.function_mapping.get(function_name)

            if not analysis_fn:
                raise ValueError(
                    f"Analysis function for metric '{analysis.metric_code}' not found"
                )

            _compute_start = time.monotonic()
            result_data = analysis_fn(df, analysis)
            result_data = self._engine._sanitize_value(result_data)
            _compute_duration = round(time.monotonic() - _compute_start, 3)

            AnalysisResult.objects.create(
                analysis=analysis,
                chart_data=result_data["chart_data"],
                chart_image=result_data.get("chart_image"),
                statistics=result_data.get("statistics"),
            )

            analysis.status = "completed"
            analysis.completed_at = timezone.now()
            analysis.save()

            _total_duration = round(time.monotonic() - _start, 3)
            logger.info(
                "Analysis pipeline completed",
                extra={
                    "analysis_id": str(analysis.id),
                    "metric": metric_code,
                    "dataset_id": dataset_id,
                    "rows": len(df),
                    "duration": _total_duration,
                    "load_duration": _load_duration,
                    "compute_duration": _compute_duration,
                    "status": "success",
                    "event": "analysis_completed",
                },
            )

        except Exception as exc:
            _total_duration = round(time.monotonic() - _start, 3)
            analysis.status = "failed"
            analysis.error_message = str(exc)
            analysis.save()
            logger.error(
                "Analysis pipeline failed",
                extra={
                    "analysis_id": str(analysis.id),
                    "metric": metric_code,
                    "dataset_id": dataset_id,
                    "status": "failed",
                    "error": str(exc),
                    "duration": _total_duration,
                    "event": "analysis_failed",
                },
                exc_info=True,
            )

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

    def _apply_custom_formula_if_needed(
        self, df: pd.DataFrame, analysis, dataset_service: DatasetService
    ) -> pd.DataFrame:
        if analysis.metric_code != CUSTOM_FORMULA_METRIC_CODE:
            return df

        config = dict(analysis.config or {})
        output_column = slugify_output_column(
            config.get("output_column") or config.get("name") or "custom_metric"
        )
        formula_result = evaluate_formula(
            df=df,
            formula=config.get("formula", ""),
            output_column=output_column,
        )

        config["output_column"] = formula_result.output_column
        config.setdefault("y_axis", formula_result.output_column)
        analysis.config = config
        analysis.save(update_fields=["config", "updated_at"])

        if config.get("persist_column", True):
            dataset_service.save_dataframe(analysis.dataset, formula_result.dataframe)

        return formula_result.dataframe
