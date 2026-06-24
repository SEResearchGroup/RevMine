from __future__ import annotations

import logging

import pandas as pd

from analytics.domain.analysis.custom_formula import (
    CUSTOM_FORMULA_METRIC_CODE,
    evaluate_formula,
    slugify_output_column,
)
from analytics.domain.metrics.providers.base import register_provider

logger = logging.getLogger(__name__)


class CustomFormulaProvider:
    """Evaluates user-defined formulas and enriches the DataFrame before chart generation.

    Extracted from AnalysisService so the pipeline no longer contains a hard-coded
    ``if metric_code == "custom_formula"`` branch.
    """

    metric_code: str = CUSTOM_FORMULA_METRIC_CODE

    def prepare_dataframe(
        self,
        df: pd.DataFrame,
        analysis,
        dataset_service,
    ) -> pd.DataFrame:
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


# Self-register when the module is imported.
register_provider(CustomFormulaProvider())
