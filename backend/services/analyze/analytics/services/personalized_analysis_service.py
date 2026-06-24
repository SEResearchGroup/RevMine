"""PersonalizedAnalysisService — top-level orchestrator for the NL→chart pipeline.

Pipeline stages
---------------
1. AnalysisPlanner   — converts a natural-language prompt into an AnalysisPlan via LLM
2. MetricResolver    — validates the plan against the dataset columns
3. DatasetService    — loads the CSV as a pandas DataFrame
4. ScriptExecutor    — evaluates the formula to produce a derived column (if needed)
5. ChartGenerator    — delegates to MetricsEngine to build chart_data + image + statistics
6. ResultStorage     — persists Analysis + AnalysisResult to the database

Usage
-----
    result = PersonalizedAnalysisService().execute(
        dataset=dataset,
        prompt="La moyenne de changements par auteur",
        llm_provider="openrouter",
        model="anthropic/claude-sonnet-4-6",
    )
"""
from __future__ import annotations

import logging

import pandas as pd

from analytics.pipeline.analysis_planner import AnalysisPlanner, AnalysisPlannerError
from analytics.pipeline.chart_generator import ChartGenerator
from analytics.pipeline.metric_resolver import MetricResolver, MetricResolverError
from analytics.pipeline.result_storage import ResultStorage
from analytics.pipeline.script_executor import ScriptExecutor, ScriptExecutorError
from analytics.pipeline.base import AnalysisRequest, PipelineResult
from analytics.services.dataset_service import DatasetService

logger = logging.getLogger(__name__)

_DATE_COLUMNS = ["Creation_Date", "created_at", "updated_at", "merged_at", "closed_at"]


class PersonalizedAnalysisError(RuntimeError):
    """Public error raised by PersonalizedAnalysisService for caller-facing messages."""


class PersonalizedAnalysisService:
    """End-to-end orchestrator: natural language → persisted chart."""

    def __init__(self) -> None:
        self._chart_generator = ChartGenerator()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(
        self,
        dataset,
        prompt: str,
        llm_provider: str = "openrouter",
        model: str = "anthropic/claude-sonnet-4-6",
    ) -> PipelineResult:
        request = AnalysisRequest(
            prompt=prompt,
            dataset_id=str(dataset.id),
            columns_metadata=dataset.columns_metadata or {},
            llm_provider=llm_provider,
            model=model,
        )

        logger.info(
            "Personalized analysis pipeline started",
            extra={
                "dataset_id": str(dataset.id),
                "prompt_length": len(prompt),
                "provider": llm_provider,
                "model": model,
                "event": "personalized_analysis_started",
            },
        )

        # --- Stage 1: plan ---
        try:
            plan = AnalysisPlanner.plan(request)
        except AnalysisPlannerError as exc:
            raise PersonalizedAnalysisError(str(exc)) from exc

        # --- Stage 2: resolve ---
        warnings: list[str] = []
        try:
            plan = MetricResolver.resolve(plan, request.columns_metadata, warnings)
        except MetricResolverError as exc:
            raise PersonalizedAnalysisError(str(exc)) from exc

        # --- Stage 3: load dataset ---
        df = DatasetService().load_dataframe(dataset)
        df = self._parse_dates(df)

        # --- Stage 4: execute formula ---
        try:
            df_enriched, output_column = ScriptExecutor.execute(plan, df)
        except ScriptExecutorError as exc:
            raise PersonalizedAnalysisError(str(exc)) from exc

        # --- Stage 5: generate chart ---
        chart_result = self._chart_generator.generate(df_enriched, plan, output_column)

        # --- Stage 6: persist ---
        result = ResultStorage.store(
            dataset=dataset,
            plan=plan,
            output_column=output_column,
            chart_result=chart_result,
            df_with_derived=df_enriched,
            warnings=warnings,
        )

        logger.info(
            "Personalized analysis pipeline completed",
            extra={
                "dataset_id": str(dataset.id),
                "analysis_id": result.analysis_id,
                "scenario": plan.scenario,
                "event": "personalized_analysis_completed",
            },
        )

        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_dates(df: pd.DataFrame) -> pd.DataFrame:
        df_copy = df.copy()
        for col in _DATE_COLUMNS:
            if col in df_copy.columns:
                df_copy[col] = pd.to_datetime(df_copy[col], errors="coerce", format="mixed")
        return df_copy
