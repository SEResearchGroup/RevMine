"""
DSL Validator
=============
Two-pass validation for Analysis DSL documents:

Pass 1 — Structural (jsonschema):  field types, enum values, required fields.
Pass 2 — Semantic:                 referenced columns exist in the dataset,
                                   aggregation is compatible with column type,
                                   derived_column formula uses only known columns.

Usage:
    validator = DSLValidator(available_columns={"Lead_Time": "numeric", ...})
    dsl = validator.parse(raw_dict)  # raises DSLValidationError on failure
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

try:
    import jsonschema
    _HAS_JSONSCHEMA = True
except ImportError:
    _HAS_JSONSCHEMA = False

from analytics.domain.dsl.schema import (
    ALLOWED_FILTER_OPS,
    DSL_JSON_SCHEMA,
    DSL_SCHEMA_VERSION,
    AnalysisDSL,
    DSLChart,
    DSLDerivedColumn,
    DSLFilter,
    DSLGroupBy,
    DSLSelect,
    DSLSeries,
    DSLSort,
    DSLSource,
)


class DSLValidationError(Exception):
    """Raised when an Analysis DSL document fails validation."""

    def __init__(self, message: str, field: Optional[str] = None, suggestion: Optional[str] = None):
        super().__init__(message)
        self.field = field
        self.suggestion = suggestion

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": "dsl_validation_error",
            "message": str(self),
            "field": self.field,
            "suggestion": self.suggestion,
        }


# Simple arithmetic formula: col1 / col2, col1 * col2, col1 + col2, col1 - col2
# or a constant like rework_size / initial_mr_size
_FORMULA_RE = re.compile(
    r"^(?P<lhs>[A-Za-z_#][A-Za-z0-9_#]*)\s*(?P<op>[+\-*/])\s*(?P<rhs>[A-Za-z_#][A-Za-z0-9_#]*)$"
)


class DSLValidator:
    """
    Validates and parses a raw dict into an AnalysisDSL dataclass.

    Parameters
    ----------
    available_columns : dict
        Mapping of column_name → type string (e.g. "numeric", "datetime",
        "categorical").  When provided, semantic column checks are enabled.
        When None, only structural validation runs.
    """

    def __init__(self, available_columns: Optional[Dict[str, str]] = None):
        self.available_columns = available_columns or {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, raw: Dict[str, Any]) -> AnalysisDSL:
        """
        Full validation + parsing pipeline.
        Returns an AnalysisDSL or raises DSLValidationError.
        """
        self._structural_validate(raw)
        dsl = self._parse_dsl(raw)
        self._semantic_validate(dsl)
        return dsl

    def validate_only(self, raw: Dict[str, Any]) -> List[str]:
        """
        Run both passes and return a list of error messages.
        Returns an empty list if the document is valid.
        """
        errors: List[str] = []
        try:
            self._structural_validate(raw)
        except DSLValidationError as exc:
            errors.append(str(exc))
            return errors

        try:
            dsl = self._parse_dsl(raw)
            self._semantic_validate(dsl)
        except DSLValidationError as exc:
            errors.append(str(exc))
        return errors

    # ------------------------------------------------------------------
    # Pass 1 — Structural
    # ------------------------------------------------------------------

    def _structural_validate(self, raw: Dict[str, Any]) -> None:
        if not isinstance(raw, dict):
            raise DSLValidationError("DSL must be a JSON object.")

        version = raw.get("version")
        if version != DSL_SCHEMA_VERSION:
            raise DSLValidationError(
                f"Unsupported DSL version '{version}'. Expected '{DSL_SCHEMA_VERSION}'.",
                field="version",
            )

        if _HAS_JSONSCHEMA:
            try:
                jsonschema.validate(instance=raw, schema=DSL_JSON_SCHEMA)
            except jsonschema.ValidationError as exc:
                path = " → ".join(str(p) for p in exc.absolute_path)
                raise DSLValidationError(
                    exc.message,
                    field=path or None,
                ) from exc
        else:
            # Fallback: manual checks for the most critical constraints
            self._manual_structural_checks(raw)

    def _manual_structural_checks(self, raw: Dict[str, Any]) -> None:
        chart = raw.get("chart", {})
        chart_type = chart.get("type", "bar")
        from analytics.domain.dsl.schema import ALLOWED_CHART_TYPES, ALLOWED_AGGREGATIONS, ALLOWED_FILTER_OPS
        if chart_type not in ALLOWED_CHART_TYPES:
            raise DSLValidationError(
                f"Unknown chart type '{chart_type}'.", field="chart.type"
            )

        select = raw.get("select", {})
        agg = select.get("aggregation")
        if agg and agg not in ALLOWED_AGGREGATIONS:
            raise DSLValidationError(
                f"Unknown aggregation '{agg}'.", field="select.aggregation"
            )

        for i, flt in enumerate(raw.get("filters", [])):
            op = flt.get("op")
            if op not in ALLOWED_FILTER_OPS:
                raise DSLValidationError(
                    f"Unknown filter operator '{op}'.", field=f"filters[{i}].op"
                )

    # ------------------------------------------------------------------
    # Parsing — dict → AnalysisDSL
    # ------------------------------------------------------------------

    def _parse_dsl(self, raw: Dict[str, Any]) -> AnalysisDSL:
        source_raw = raw.get("source", {})
        source = DSLSource(
            type=source_raw.get("type", "reviews"),
            dataset_id=source_raw.get("dataset_id"),
        )

        select_raw = raw.get("select", {})
        select = DSLSelect(
            metric=select_raw.get("metric"),
            metrics=select_raw.get("metrics", []),
            aggregation=select_raw.get("aggregation", "avg"),
        )

        group_raw = raw.get("group_by", {})
        time_raw = group_raw.get("time", {})
        group_by = DSLGroupBy(
            column=group_raw.get("column"),
            time_column=time_raw.get("column") if time_raw else None,
            time_period=time_raw.get("period") if time_raw else None,
        )

        filters = [
            DSLFilter(column=f["column"], op=f["op"], value=f.get("value"))
            for f in raw.get("filters", [])
        ]

        sort_raw = raw.get("sort", {})
        sort = DSLSort(
            by=sort_raw.get("by", "value"),
            order=sort_raw.get("order", "desc"),
        )

        chart_raw = raw.get("chart", {})
        chart = DSLChart(
            type=chart_raw.get("type", "bar"),
            x_label=chart_raw.get("x_label"),
            y_label=chart_raw.get("y_label"),
            stack=chart_raw.get("stack", False),
            bin_count=chart_raw.get("bin_count", 30),
            confidence_interval=chart_raw.get("confidence_interval"),
            trend_line=chart_raw.get("trend_line", False),
        )

        series = [
            DSLSeries(
                metric=s["metric"],
                aggregation=s["aggregation"],
                label=s.get("label", s["metric"]),
                color=s.get("color"),
            )
            for s in raw.get("series", [])
        ]

        derived_raw = raw.get("derived_column")
        derived = None
        if derived_raw:
            derived = DSLDerivedColumn(
                name=derived_raw["name"],
                formula=derived_raw["formula"],
                type=derived_raw.get("type", "ratio"),
            )

        return AnalysisDSL(
            version=raw.get("version", DSL_SCHEMA_VERSION),
            source=source,
            select=select,
            group_by=group_by,
            filters=filters,
            sort=sort,
            limit=raw.get("limit"),
            chart=chart,
            secondary_metric=raw.get("secondary_metric"),
            series=series,
            derived_column=derived,
        )

    # ------------------------------------------------------------------
    # Pass 2 — Semantic
    # ------------------------------------------------------------------

    def _semantic_validate(self, dsl: AnalysisDSL) -> None:
        if not self.available_columns:
            return  # No column info available; skip semantic pass.

        cols = set(self.available_columns.keys())

        # Validate selected metrics exist (derived column names are allowed even if not in original columns)
        derived_names = {dsl.derived_column.name} if dsl.derived_column else set()
        if dsl.select.metric and dsl.select.metric not in derived_names:
            self._check_column(dsl.select.metric, cols, "select.metric")
        for m in dsl.select.metrics:
            if m not in derived_names:
                self._check_column(m, cols, "select.metrics")

        # Validate group_by columns
        if dsl.group_by.column:
            self._check_column(dsl.group_by.column, cols, "group_by.column")
        if dsl.group_by.time_column:
            self._check_column(dsl.group_by.time_column, cols, "group_by.time.column")
            col_type = self._col_type(dsl.group_by.time_column)
            col_meta = self.available_columns.get(dsl.group_by.time_column, {})
            parseable_as_dt = isinstance(col_meta, dict) and col_meta.get("parseable_as_datetime", False)
            if col_type not in ("datetime", "datetime_string") and not parseable_as_dt:
                raise DSLValidationError(
                    f"Column '{dsl.group_by.time_column}' must be a datetime column for time aggregation. "
                    f"Detected type: '{col_type}'.",
                    field="group_by.time.column",
                )

        # Validate filter columns
        for i, flt in enumerate(dsl.filters):
            self._check_column(flt.column, cols, f"filters[{i}].column")
            self._validate_filter_value(flt, i)

        # Validate secondary metric
        if dsl.secondary_metric:
            self._check_column(dsl.secondary_metric, cols, "secondary_metric")

        # Validate series metrics
        for i, s in enumerate(dsl.series):
            self._check_column(s.metric, cols, f"series[{i}].metric")

        # Validate derived column formula
        if dsl.derived_column:
            self._validate_derived_column(dsl.derived_column, cols)

        # Heatmap requires at least 2 metrics
        if dsl.is_heatmap:
            metric_list = dsl.select.metrics
            if len(metric_list) < 2:
                raise DSLValidationError(
                    "Heatmap requires at least 2 metrics in 'select.metrics'.",
                    field="select.metrics",
                )

    def _col_type(self, col_name: str) -> str:
        """Return type string for a column, handling both str and dict metadata values."""
        val = self.available_columns.get(col_name, "")
        if isinstance(val, dict):
            return val.get("type", "numeric")
        return val or ""

    def _check_column(self, col: str, available: set, field: str) -> None:
        if col not in available:
            suggestion = self._suggest_column(col, available)
            raise DSLValidationError(
                f"Column '{col}' not found in dataset.",
                field=field,
                suggestion=f"Did you mean '{suggestion}'?" if suggestion else None,
            )

    def _suggest_column(self, name: str, available: set) -> Optional[str]:
        """Simple fuzzy suggestion: find column with most shared characters."""
        name_lower = name.lower()
        best, best_score = None, 0
        for col in available:
            score = sum(c in col.lower() for c in name_lower)
            if score > best_score:
                best, best_score = col, score
        return best if best_score > 0 else None

    def _validate_filter_value(self, flt: DSLFilter, idx: int) -> None:
        op = flt.op
        if op in ("eq", "neq", "gt", "gte", "lt", "lte", "contains"):
            if flt.value is None:
                raise DSLValidationError(
                    f"Filter[{idx}] operator '{op}' requires a 'value'.",
                    field=f"filters[{idx}].value",
                )
        elif op in ("in", "not_in"):
            if not isinstance(flt.value, list):
                raise DSLValidationError(
                    f"Filter[{idx}] operator '{op}' requires a list 'value'.",
                    field=f"filters[{idx}].value",
                )
        elif op == "between":
            if not isinstance(flt.value, list) or len(flt.value) != 2:
                raise DSLValidationError(
                    f"Filter[{idx}] operator 'between' requires a list of exactly 2 values.",
                    field=f"filters[{idx}].value",
                )

    def _validate_derived_column(self, derived: DSLDerivedColumn, cols: set) -> None:
        m = _FORMULA_RE.match(derived.formula.strip())
        if not m:
            raise DSLValidationError(
                f"Derived column formula '{derived.formula}' must be a simple arithmetic expression "
                f"between two existing columns (e.g. 'rework_size / initial_mr_size').",
                field="derived_column.formula",
            )
        lhs, rhs = m.group("lhs"), m.group("rhs")
        for operand in (lhs, rhs):
            if operand not in cols:
                suggestion = self._suggest_column(operand, cols)
                raise DSLValidationError(
                    f"Derived column formula references unknown column '{operand}'.",
                    field="derived_column.formula",
                    suggestion=f"Did you mean '{suggestion}'?" if suggestion else None,
                )
