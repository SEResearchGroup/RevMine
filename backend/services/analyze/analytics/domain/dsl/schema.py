"""
Analysis DSL Schema v1
======================
Defines the JSON contract for user-requested analyses.

The LLM generates a document conforming to this schema.
The DSLExecutionEngine interprets and executes it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

DSL_SCHEMA_VERSION = "1"

# ------------------------------------------------------------------
# Allowed enumerated values (used by validator and LLM prompt)
# ------------------------------------------------------------------

ALLOWED_AGGREGATIONS = {"avg", "sum", "count", "min", "max", "median", "std", "p95", "p99"}
ALLOWED_CHART_TYPES = {"bar", "line", "scatter", "histogram", "pie", "heatmap", "box", "area", "multi_bar"}
ALLOWED_SORT_ORDERS = {"asc", "desc"}
ALLOWED_SORT_BY = {"value", "label"}
ALLOWED_TIME_PERIODS = {"day", "week", "month", "quarter", "year"}
ALLOWED_SOURCE_TYPES = {"reviews", "kanban", "cicd"}
ALLOWED_FILTER_OPS = {"eq", "neq", "gt", "gte", "lt", "lte", "in", "not_in", "between", "contains", "not_null"}

# Map DSL period name → pandas Period alias
PERIOD_TO_PANDAS = {
    "day": "D",
    "week": "W",
    "month": "M",
    "quarter": "Q",
    "year": "Y",
}

# Map DSL aggregation → pandas/numpy method
AGG_TO_PANDAS = {
    "avg": "mean",
    "sum": "sum",
    "count": "count",
    "min": "min",
    "max": "max",
    "median": "median",
    "std": "std",
    "p95": lambda x: x.quantile(0.95),
    "p99": lambda x: x.quantile(0.99),
}


# ------------------------------------------------------------------
# JSON Schema (for jsonschema validation)
# ------------------------------------------------------------------

DSL_JSON_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["version", "source"],
    "additionalProperties": False,
    "properties": {
        "$schema": {"type": "string"},
        "version": {"type": "string", "enum": [DSL_SCHEMA_VERSION]},
        "source": {
            "type": "object",
            "properties": {
                "dataset_id": {"type": ["string", "null"]},
                "type": {"type": "string", "enum": list(ALLOWED_SOURCE_TYPES)},
            },
        },
        "select": {
            "type": "object",
            "properties": {
                "metric": {"type": "string"},
                "metrics": {"type": "array", "items": {"type": "string"}},
                "aggregation": {"type": "string", "enum": list(ALLOWED_AGGREGATIONS)},
            },
        },
        "group_by": {
            "type": "object",
            "properties": {
                "column": {"type": ["string", "null"]},
                "time": {
                    "type": "object",
                    "required": ["column", "period"],
                    "properties": {
                        "column": {"type": "string"},
                        "period": {"type": "string", "enum": list(ALLOWED_TIME_PERIODS)},
                    },
                },
            },
        },
        "filters": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["column", "op"],
                "properties": {
                    "column": {"type": "string"},
                    "op": {"type": "string", "enum": list(ALLOWED_FILTER_OPS)},
                    "value": {},
                },
            },
        },
        "sort": {
            "type": "object",
            "properties": {
                "by": {"type": "string", "enum": list(ALLOWED_SORT_BY)},
                "order": {"type": "string", "enum": list(ALLOWED_SORT_ORDERS)},
            },
        },
        "limit": {"type": ["integer", "null"], "minimum": 1},
        "chart": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": list(ALLOWED_CHART_TYPES)},
                "x_label": {"type": ["string", "null"]},
                "y_label": {"type": ["string", "null"]},
                "stack": {"type": "boolean"},
                "bin_count": {"type": ["integer", "null"], "minimum": 2, "maximum": 200},
                "confidence_interval": {"type": ["integer", "null"], "minimum": 50, "maximum": 99},
                "trend_line": {"type": "boolean"},
            },
        },
        "secondary_metric": {"type": ["string", "null"]},
        "series": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["metric", "aggregation"],
                "properties": {
                    "metric": {"type": "string"},
                    "aggregation": {"type": "string", "enum": list(ALLOWED_AGGREGATIONS)},
                    "label": {"type": "string"},
                    "color": {"type": ["string", "null"]},
                },
            },
        },
        "derived_column": {
            "type": "object",
            "required": ["name", "formula"],
            "properties": {
                "name": {"type": "string"},
                "formula": {"type": "string"},
                "type": {"type": "string", "enum": ["ratio", "sum", "difference", "product"]},
            },
        },
    },
}


# ------------------------------------------------------------------
# Python dataclass representation (parsed from the incoming JSON)
# ------------------------------------------------------------------

@dataclass
class DSLFilter:
    column: str
    op: str
    value: Any = None


@dataclass
class DSLSeries:
    metric: str
    aggregation: str
    label: str = ""
    color: Optional[str] = None


@dataclass
class DSLSort:
    by: str = "value"
    order: str = "desc"


@dataclass
class DSLChart:
    type: str = "bar"
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    stack: bool = False
    bin_count: Optional[int] = 30
    confidence_interval: Optional[int] = None
    trend_line: bool = False


@dataclass
class DSLSource:
    type: str = "reviews"
    dataset_id: Optional[str] = None


@dataclass
class DSLSelect:
    metric: Optional[str] = None
    metrics: List[str] = field(default_factory=list)
    aggregation: str = "avg"


@dataclass
class DSLGroupBy:
    column: Optional[str] = None
    time_column: Optional[str] = None
    time_period: Optional[str] = None


@dataclass
class DSLDerivedColumn:
    name: str = ""
    formula: str = ""
    type: str = "ratio"


@dataclass
class AnalysisDSL:
    """
    Parsed representation of an Analysis DSL document.
    Created by DSLValidator.parse() after structural and semantic validation.
    """
    version: str = DSL_SCHEMA_VERSION
    source: DSLSource = field(default_factory=DSLSource)
    select: DSLSelect = field(default_factory=DSLSelect)
    group_by: DSLGroupBy = field(default_factory=DSLGroupBy)
    filters: List[DSLFilter] = field(default_factory=list)
    sort: DSLSort = field(default_factory=DSLSort)
    limit: Optional[int] = None
    chart: DSLChart = field(default_factory=DSLChart)
    secondary_metric: Optional[str] = None
    series: List[DSLSeries] = field(default_factory=list)
    derived_column: Optional[DSLDerivedColumn] = None

    @property
    def is_multi_series(self) -> bool:
        return len(self.series) > 0

    @property
    def is_time_series(self) -> bool:
        return self.group_by.time_column is not None

    @property
    def is_scatter(self) -> bool:
        return self.chart.type == "scatter"

    @property
    def is_histogram(self) -> bool:
        return self.chart.type == "histogram"

    @property
    def is_heatmap(self) -> bool:
        return self.chart.type == "heatmap"

    @property
    def primary_metric(self) -> Optional[str]:
        """Returns the single metric name for non-multi-series analyses."""
        if self.select.metric:
            return self.select.metric
        if self.select.metrics:
            return self.select.metrics[0]
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize back to a plain dict (for storage in dsl_config JSONField)."""
        d: Dict[str, Any] = {
            "version": self.version,
            "source": {"type": self.source.type},
        }
        if self.source.dataset_id:
            d["source"]["dataset_id"] = self.source.dataset_id

        if self.select.metric or self.select.metrics or self.select.aggregation != "avg":
            d["select"] = {}
            if self.select.metric:
                d["select"]["metric"] = self.select.metric
            if self.select.metrics:
                d["select"]["metrics"] = self.select.metrics
            d["select"]["aggregation"] = self.select.aggregation

        if self.group_by.column or self.group_by.time_column:
            d["group_by"] = {}
            if self.group_by.column:
                d["group_by"]["column"] = self.group_by.column
            if self.group_by.time_column:
                d["group_by"]["time"] = {
                    "column": self.group_by.time_column,
                    "period": self.group_by.time_period or "month",
                }

        if self.filters:
            d["filters"] = [
                {"column": f.column, "op": f.op, "value": f.value}
                for f in self.filters
            ]

        if self.sort.by != "value" or self.sort.order != "desc":
            d["sort"] = {"by": self.sort.by, "order": self.sort.order}

        if self.limit is not None:
            d["limit"] = self.limit

        d["chart"] = {"type": self.chart.type}
        if self.chart.x_label:
            d["chart"]["x_label"] = self.chart.x_label
        if self.chart.y_label:
            d["chart"]["y_label"] = self.chart.y_label
        if self.chart.stack:
            d["chart"]["stack"] = self.chart.stack
        if self.chart.bin_count and self.chart.bin_count != 30:
            d["chart"]["bin_count"] = self.chart.bin_count
        if self.chart.confidence_interval:
            d["chart"]["confidence_interval"] = self.chart.confidence_interval
        if self.chart.trend_line:
            d["chart"]["trend_line"] = True

        if self.secondary_metric:
            d["secondary_metric"] = self.secondary_metric

        if self.series:
            d["series"] = [
                {"metric": s.metric, "aggregation": s.aggregation, "label": s.label}
                for s in self.series
            ]

        if self.derived_column:
            d["derived_column"] = {
                "name": self.derived_column.name,
                "formula": self.derived_column.formula,
                "type": self.derived_column.type,
            }

        return d
