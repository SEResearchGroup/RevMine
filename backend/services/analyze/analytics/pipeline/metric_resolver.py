"""MetricResolver — validates a plan against the dataset and assigns the final scenario."""
from __future__ import annotations

from analytics.domain.analysis.custom_formula import referenced_columns
from analytics.pipeline.base import (
    SCENARIO_CSV_DERIVED,
    SCENARIO_CSV_EXISTING,
    SCENARIO_RAW_JSON,
    AnalysisPlan,
)


class MetricResolverError(ValueError):
    """Raised when the plan cannot be fulfilled with the available data."""


class MetricResolver:
    """Validates an AnalysisPlan against the dataset's available columns.

    Resolution rules
    ----------------
    csv_existing / csv_derived
        All columns referenced in the formula must exist in the dataset.
        If any are missing, raises MetricResolverError.

    raw_json
        The analysis requires data that is not present in the CSV (e.g. commit
        messages, file diffs).  Full support for this scenario is planned in a
        future release; for now a descriptive error is raised so the user
        knows why the request cannot be fulfilled from the current dataset.
    """

    @staticmethod
    def resolve(
        plan: AnalysisPlan,
        columns_metadata: dict,
        warnings: list[str],
    ) -> AnalysisPlan:
        if plan.scenario == SCENARIO_RAW_JSON:
            raise MetricResolverError(
                "This analysis requires data that is not available in the CSV dataset "
                f"(scenario: raw_json). {plan.explanation}\n"
                "Tip: re-collect the repository with the required metrics and try again."
            )

        if plan.scenario in (SCENARIO_CSV_EXISTING, SCENARIO_CSV_DERIVED):
            if not plan.formula:
                return plan

            # Case-insensitive match so [lead_time] finds "Lead_Time"
            available_lower = {c.lower(): c for c in columns_metadata.keys()}
            missing = [
                col
                for col in referenced_columns(plan.formula)
                if col.lower() not in available_lower
            ]
            if missing:
                raise MetricResolverError(
                    f"The formula references columns that are not in the dataset: {missing}. "
                    "Available columns: " + ", ".join(sorted(columns_metadata.keys()))
                )

        return plan
