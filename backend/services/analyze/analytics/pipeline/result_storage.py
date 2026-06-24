"""ResultStorage — persists a completed pipeline run to the database."""
from __future__ import annotations

from django.utils import timezone

from analytics.models import Analysis, AnalysisResult
from analytics.pipeline.base import AnalysisPlan, PipelineResult
from analytics.services.dataset_service import DatasetService

import pandas as pd


class ResultStorage:
    """Creates Analysis + AnalysisResult records from a finished pipeline execution."""

    @staticmethod
    def store(
        dataset,
        plan: AnalysisPlan,
        output_column: str,
        chart_result: dict,
        df_with_derived: pd.DataFrame,
        warnings: list[str],
    ) -> PipelineResult:
        config = {
            "name": plan.name,
            "formula": plan.formula,
            "output_column": output_column,
            "aggregation_scope": plan.aggregation_scope,
            "aggregation": plan.aggregation,
            "chart_type": plan.chart_type,
            "time_aggregation": plan.time_aggregation,
            "x_axis": plan.x_axis,
            "scenario": plan.scenario,
            "persist_column": bool(plan.formula),
        }

        analysis = Analysis.objects.create(
            dataset=dataset,
            metric_code="custom_formula",
            chart_type=plan.chart_type,
            config=config,
            status="completed",
            completed_at=timezone.now(),
        )

        if plan.formula:
            DatasetService().save_dataframe(dataset, df_with_derived)

        analysis_result = AnalysisResult.objects.create(
            analysis=analysis,
            chart_data=chart_result["chart_data"],
            chart_image=chart_result.get("chart_image"),
            statistics=chart_result.get("statistics"),
        )

        return PipelineResult(
            plan=plan,
            chart_data=analysis_result.chart_data,
            chart_image=analysis_result.chart_image,
            statistics=analysis_result.statistics or {},
            analysis_id=str(analysis.id),
            dataset_id=str(dataset.id),
            output_column=output_column,
            warnings=warnings,
        )
