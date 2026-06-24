"""Shared data-types for the personalized-analysis pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Supported scenarios — determines where the data comes from.
SCENARIO_CSV_EXISTING = "csv_existing"   # all columns already exist in the CSV
SCENARIO_CSV_DERIVED = "csv_derived"     # metric computed from CSV columns via arithmetic
SCENARIO_RAW_JSON = "raw_json"           # requires raw collection JSON (not yet supported)


@dataclass
class AnalysisRequest:
    """Input handed to the pipeline by the API view."""

    prompt: str
    dataset_id: str
    columns_metadata: dict[str, Any]
    llm_provider: str = "openrouter"
    model: str = "anthropic/claude-sonnet-4-6"


@dataclass
class AnalysisPlan:
    """Everything the pipeline needs in order to execute an analysis.

    Produced by AnalysisPlanner and validated by MetricResolver.
    """

    scenario: str                           # one of SCENARIO_* constants
    name: str                               # short display name for the chart
    explanation: str                        # why this approach was chosen
    formula: str | None                     # pandas arithmetic expression (csv_existing / csv_derived)
    output_column: str | None               # snake_case name for the derived column
    metrics_needed: list[str] = field(default_factory=list)
    aggregation_scope: str = "mr"           # "mr" | "time" | "category"
    aggregation: str = "mean"              # "sum" | "mean" | "median" | "count" | "min" | "max" | "std"
    chart_type: str = "bar"                # "bar" | "line" | "area" | "scatter"
    x_axis: str | None = None
    time_aggregation: str = "M"            # "D" | "W" | "M" | "Q" | "Y"


@dataclass
class PipelineResult:
    """Final output of the personalized-analysis pipeline."""

    plan: AnalysisPlan
    chart_data: dict
    chart_image: str | None
    statistics: dict
    analysis_id: str
    dataset_id: str
    output_column: str
    warnings: list[str] = field(default_factory=list)
