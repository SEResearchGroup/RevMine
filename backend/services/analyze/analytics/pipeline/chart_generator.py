"""ChartGenerator — delegates chart creation to MetricsEngine."""
from __future__ import annotations

import pandas as pd

from analytics.pipeline.base import AnalysisPlan


class _MockAnalysis:
    """Minimal stand-in for the Django Analysis ORM object expected by MetricsEngine."""

    def __init__(self, config: dict, chart_type: str) -> None:
        self.config = config
        self.chart_type = chart_type


class ChartGenerator:
    """Generates a chart dict (chart_data + chart_image + statistics) from a pipeline plan."""

    def __init__(self) -> None:
        from analytics.domain.metrics.metrics_engine import MetricsEngine

        self._engine = MetricsEngine()

    def generate(
        self,
        df: pd.DataFrame,
        plan: AnalysisPlan,
        output_column: str,
    ) -> dict:
        config = {
            "name": plan.name,
            "formula": plan.formula,
            "output_column": output_column,
            "y_axis": output_column,
            "aggregation_scope": plan.aggregation_scope,
            "aggregation": plan.aggregation,
            "chart_type": plan.chart_type,
            "time_aggregation": plan.time_aggregation,
        }
        if plan.x_axis:
            config["x_axis"] = plan.x_axis

        mock = _MockAnalysis(config=config, chart_type=plan.chart_type)
        result = self._engine.analyze_custom_formula(df, mock)
        return self._engine._sanitize_value(result)
