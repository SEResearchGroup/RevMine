"""ScriptExecutor — applies a plan's formula to a DataFrame safely."""
from __future__ import annotations

import pandas as pd

from analytics.domain.analysis.custom_formula import evaluate_formula, slugify_output_column
from analytics.pipeline.base import (
    SCENARIO_CSV_DERIVED,
    SCENARIO_CSV_EXISTING,
    AnalysisPlan,
)


class ScriptExecutorError(RuntimeError):
    """Raised when formula execution fails."""


class ScriptExecutor:
    """Applies the formula from an AnalysisPlan to produce a derived column.

    Scenarios
    ---------
    csv_existing (with formula)
        The formula may reference existing columns with arithmetic — treated
        identically to csv_derived.

    csv_existing (no formula)
        The chart is built directly from an existing column identified by
        ``plan.output_column`` or ``plan.x_axis``.  The DataFrame is returned
        unchanged; the caller passes the relevant column name to ChartGenerator.

    csv_derived
        A new column is derived by evaluating ``plan.formula``.

    Returns
    -------
    (df, output_column)
        The (possibly enriched) DataFrame and the name of the column that
        ChartGenerator should visualise.
    """

    @staticmethod
    def execute(plan: AnalysisPlan, df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
        if plan.scenario in (SCENARIO_CSV_EXISTING, SCENARIO_CSV_DERIVED):
            if plan.formula:
                output_col = plan.output_column or slugify_output_column(plan.name)
                try:
                    result = evaluate_formula(df, plan.formula, output_col)
                except Exception as exc:
                    raise ScriptExecutorError(
                        f"Formula evaluation failed: {exc}"
                    ) from exc
                return result.dataframe, result.output_column

            # No formula — use an existing column directly.
            # Try case-insensitive lookup so "lead_time" matches "Lead_Time".
            col_lower_map = {c.lower(): c for c in df.columns}
            for candidate in (plan.output_column, plan.x_axis):
                if not candidate:
                    continue
                resolved = col_lower_map.get(candidate.lower(), candidate)
                if resolved in df.columns:
                    return df, resolved

            raise ScriptExecutorError(
                "No formula and no valid column reference found in the plan. "
                f"output_column={plan.output_column!r}, x_axis={plan.x_axis!r}. "
                f"Available columns: {sorted(df.columns.tolist())}"
            )

        raise ScriptExecutorError(f"Unsupported scenario: {plan.scenario!r}")
