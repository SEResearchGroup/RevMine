"""
Unit tests for the DSL-First Custom Analysis pipeline.

Tests cover:
- DSL schema / dataclass construction
- DSLValidator (structural + semantic passes)
- Operators: FilterApplier, DerivedColumnBuilder, Aggregator, Sorter
- DSLExecutionEngine end-to-end
- ValidationLayer (DSL validation path)
"""
from __future__ import annotations

import math
import pytest
import pandas as pd
import numpy as np

from analytics.domain.dsl.schema import (
    AnalysisDSL,
    DSLSource,
    DSLSelect,
    DSLGroupBy,
    DSLGroupByTime,
    DSLFilter,
    DSLSort,
    DSLChart,
    DSLSeries,
    DSLDerivedColumn,
    DSL_SCHEMA_VERSION,
)
from analytics.domain.dsl.validator import DSLValidator, DSLValidationError
from analytics.domain.dsl.operators import FilterApplier, DerivedColumnBuilder, Aggregator, Sorter
from analytics.domain.dsl.engine import DSLExecutionEngine
from analytics.domain.validation.layer import ValidationLayer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_df():
    """A minimal code-review DataFrame for testing."""
    return pd.DataFrame({
        "Author":          ["Alice", "Bob", "Alice", "Charlie", "Bob", "Alice"],
        "Lead_Time":       [5.0, 10.0, 3.0, 8.0, 12.0, 6.0],
        "churn_addition":  [100, 200, 50, 300, 150, 80],
        "churn_deletions": [20,  50,  10,  80,  30,  15],
        "rework_size":     [10,  20,  5,   30,  15,  8],
        "initial_mr_size": [100, 200, 50, 300, 150, 80],
        "State":           ["merged", "open", "merged", "merged", "open", "merged"],
        "Creation_Date":   pd.to_datetime([
            "2024-01-10", "2024-01-15", "2024-02-05",
            "2024-02-20", "2024-03-01", "2024-03-15",
        ]),
        "#Commits":        [3, 5, 2, 7, 4, 3],
    })


@pytest.fixture
def columns_metadata(sample_df):
    type_map = {
        "object":          "string",
        "float64":         "float",
        "int64":           "integer",
        "datetime64[ns]":  "datetime",
    }
    return {
        col: {"type": type_map.get(str(sample_df[col].dtype), "unknown")}
        for col in sample_df.columns
    }


def _make_simple_dsl(**overrides):
    """Build a minimal valid AnalysisDSL for bar chart (avg Lead_Time by Author)."""
    defaults = dict(
        version=DSL_SCHEMA_VERSION,
        source=DSLSource(type="reviews"),
        select=DSLSelect(metric="Lead_Time", aggregation="avg"),
        group_by=DSLGroupBy(column="Author"),
        filters=[],
        sort=DSLSort(by="value", order="desc"),
        limit=None,
        chart=DSLChart(type="bar"),
        secondary_metric=None,
        series=[],
        derived_column=None,
    )
    defaults.update(overrides)
    return AnalysisDSL(**defaults)


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

class TestDSLSchema:
    def test_simple_dsl_properties(self):
        dsl = _make_simple_dsl()
        assert not dsl.is_multi_series
        assert not dsl.is_time_series
        assert dsl.primary_metric == "Lead_Time"

    def test_multi_series_detected(self):
        dsl = _make_simple_dsl(
            series=[
                DSLSeries(metric="Lead_Time", aggregation="avg", label="avg"),
                DSLSeries(metric="Lead_Time", aggregation="p95", label="p95"),
            ],
            select=DSLSelect(metric="Lead_Time", aggregation="avg"),
        )
        assert dsl.is_multi_series

    def test_time_series_detected(self):
        dsl = _make_simple_dsl(
            group_by=DSLGroupBy(time=DSLGroupByTime(column="Creation_Date", period="month"))
        )
        assert dsl.is_time_series

    def test_to_dict_round_trip(self):
        dsl = _make_simple_dsl()
        d = dsl.to_dict()
        assert d["version"] == DSL_SCHEMA_VERSION
        assert d["select"]["metric"] == "Lead_Time"
        assert d["chart"]["type"] == "bar"


# ---------------------------------------------------------------------------
# Validator tests
# ---------------------------------------------------------------------------

class TestDSLValidator:
    def test_valid_dsl_passes(self, columns_metadata):
        raw = {
            "version": "1",
            "source": {"type": "reviews"},
            "select": {"metric": "Lead_Time", "aggregation": "avg"},
            "group_by": {"column": "Author"},
            "chart": {"type": "bar"},
        }
        validator = DSLValidator(available_columns=columns_metadata)
        dsl = validator.parse(raw)
        assert dsl.select.metric == "Lead_Time"
        assert dsl.group_by.column == "Author"

    def test_missing_version_raises(self, columns_metadata):
        raw = {"source": {"type": "reviews"}, "select": {"metric": "Lead_Time"}, "chart": {"type": "bar"}}
        validator = DSLValidator(available_columns=columns_metadata)
        with pytest.raises(DSLValidationError):
            validator.parse(raw)

    def test_unknown_column_raises(self, columns_metadata):
        raw = {
            "version": "1",
            "source": {"type": "reviews"},
            "select": {"metric": "NonExistentCol", "aggregation": "avg"},
            "chart": {"type": "bar"},
        }
        validator = DSLValidator(available_columns=columns_metadata)
        with pytest.raises(DSLValidationError) as exc_info:
            validator.parse(raw)
        assert exc_info.value.field == "select.metric"

    def test_time_groupby_requires_datetime_column(self, columns_metadata):
        raw = {
            "version": "1",
            "source": {"type": "reviews"},
            "select": {"metric": "Lead_Time", "aggregation": "avg"},
            "group_by": {"time": {"column": "Author", "period": "month"}},
            "chart": {"type": "line"},
        }
        validator = DSLValidator(available_columns=columns_metadata)
        with pytest.raises(DSLValidationError):
            validator.parse(raw)

    def test_validate_only_returns_error_list(self, columns_metadata):
        raw = {"version": "1"}  # Incomplete
        validator = DSLValidator(available_columns=columns_metadata)
        errors = validator.validate_only(raw)
        assert isinstance(errors, list)
        assert len(errors) > 0

    def test_validate_only_empty_on_valid(self, columns_metadata):
        raw = {
            "version": "1",
            "source": {"type": "reviews"},
            "select": {"metric": "Lead_Time", "aggregation": "avg"},
            "chart": {"type": "bar"},
        }
        validator = DSLValidator(available_columns=columns_metadata)
        errors = validator.validate_only(raw)
        assert errors == []


# ---------------------------------------------------------------------------
# Operators tests
# ---------------------------------------------------------------------------

class TestFilterApplier:
    def test_eq_filter(self, sample_df):
        dsl = _make_simple_dsl(filters=[
            DSLFilter(column="State", op="eq", value="merged")
        ])
        result = FilterApplier().apply(sample_df, dsl)
        assert (result["State"] == "merged").all()
        assert len(result) == 4

    def test_gt_filter(self, sample_df):
        dsl = _make_simple_dsl(filters=[
            DSLFilter(column="Lead_Time", op="gt", value=7)
        ])
        result = FilterApplier().apply(sample_df, dsl)
        assert (result["Lead_Time"] > 7).all()

    def test_in_filter(self, sample_df):
        dsl = _make_simple_dsl(filters=[
            DSLFilter(column="Author", op="in", value=["Alice", "Charlie"])
        ])
        result = FilterApplier().apply(sample_df, dsl)
        assert set(result["Author"].unique()) == {"Alice", "Charlie"}

    def test_between_filter(self, sample_df):
        dsl = _make_simple_dsl(filters=[
            DSLFilter(column="Lead_Time", op="between", value=[4, 9])
        ])
        result = FilterApplier().apply(sample_df, dsl)
        assert (result["Lead_Time"] >= 4).all()
        assert (result["Lead_Time"] <= 9).all()

    def test_not_null_filter(self, sample_df):
        df_with_null = sample_df.copy()
        df_with_null.loc[0, "Lead_Time"] = None
        dsl = _make_simple_dsl(filters=[
            DSLFilter(column="Lead_Time", op="not_null", value=None)
        ])
        result = FilterApplier().apply(df_with_null, dsl)
        assert result["Lead_Time"].notna().all()


class TestDerivedColumnBuilder:
    def test_division_formula(self, sample_df):
        dsl = _make_simple_dsl(
            derived_column=DSLDerivedColumn(
                name="rework_rate", formula="rework_size / initial_mr_size", type="ratio"
            )
        )
        result = DerivedColumnBuilder().apply(sample_df, dsl)
        assert "rework_rate" in result.columns
        expected = sample_df["rework_size"] / sample_df["initial_mr_size"]
        pd.testing.assert_series_equal(result["rework_rate"], expected, check_names=False)

    def test_addition_formula(self, sample_df):
        dsl = _make_simple_dsl(
            derived_column=DSLDerivedColumn(
                name="total_churn", formula="churn_addition + churn_deletions", type="sum"
            )
        )
        result = DerivedColumnBuilder().apply(sample_df, dsl)
        assert "total_churn" in result.columns
        expected = sample_df["churn_addition"] + sample_df["churn_deletions"]
        pd.testing.assert_series_equal(result["total_churn"], expected, check_names=False)


class TestAggregator:
    def test_group_by_column_avg(self, sample_df):
        dsl = _make_simple_dsl()
        agg = Aggregator().aggregate(sample_df, dsl)
        assert len(agg.labels) == 3  # Alice, Bob, Charlie
        assert len(agg.values) == 3
        # Alice rows: 5, 3, 6 → avg = 4.666...
        alice_idx = list(agg.labels).index("Alice")
        assert abs(agg.values[alice_idx] - (5 + 3 + 6) / 3) < 0.01

    def test_count_aggregation(self, sample_df):
        dsl = _make_simple_dsl(
            select=DSLSelect(metric="Lead_Time", aggregation="count"),
        )
        agg = Aggregator().aggregate(sample_df, dsl)
        assert sum(agg.values) == len(sample_df)

    def test_histogram(self, sample_df):
        dsl = _make_simple_dsl(
            select=DSLSelect(metric="Lead_Time"),
            group_by=DSLGroupBy(),
            chart=DSLChart(type="histogram", bin_count=5),
        )
        agg = Aggregator().aggregate(sample_df, dsl)
        assert len(agg.labels) > 0
        assert all(v >= 0 for v in agg.values)

    def test_scatter(self, sample_df):
        dsl = _make_simple_dsl(
            select=DSLSelect(metric="Lead_Time"),
            secondary_metric="churn_addition",
            chart=DSLChart(type="scatter"),
            group_by=DSLGroupBy(),
        )
        agg = Aggregator().aggregate(sample_df, dsl)
        # scatter packs x,y into values
        assert agg.extra is not None

    def test_time_series_monthly(self, sample_df):
        dsl = _make_simple_dsl(
            select=DSLSelect(metric="Lead_Time", aggregation="avg"),
            group_by=DSLGroupBy(time=DSLGroupByTime(column="Creation_Date", period="month")),
            chart=DSLChart(type="line"),
        )
        agg = Aggregator().aggregate(sample_df, dsl)
        assert len(agg.labels) >= 3  # Jan, Feb, Mar


class TestSorter:
    def test_sort_desc_by_value(self, sample_df):
        dsl = _make_simple_dsl(sort=DSLSort(by="value", order="desc"))
        agg = Aggregator().aggregate(sample_df, dsl)
        sorted_agg = Sorter().apply(agg, dsl)
        vals = sorted_agg.values
        assert all(vals[i] >= vals[i + 1] for i in range(len(vals) - 1))

    def test_limit(self, sample_df):
        dsl = _make_simple_dsl(limit=2, sort=DSLSort(by="value", order="desc"))
        agg = Aggregator().aggregate(sample_df, dsl)
        sorted_agg = Sorter().apply(agg, dsl)
        assert len(sorted_agg.labels) == 2


# ---------------------------------------------------------------------------
# DSLExecutionEngine end-to-end
# ---------------------------------------------------------------------------

class TestDSLExecutionEngine:
    def test_bar_chart_output_format(self, sample_df):
        dsl = _make_simple_dsl()
        result = DSLExecutionEngine().execute(sample_df, dsl)

        assert "chart_data" in result
        cd = result["chart_data"]
        assert cd["type"] == "bar"
        assert "data" in cd
        assert "labels" in cd["data"]
        assert "datasets" in cd["data"]
        assert len(cd["data"]["datasets"]) >= 1

    def test_statistics_computed(self, sample_df):
        dsl = _make_simple_dsl()
        result = DSLExecutionEngine().execute(sample_df, dsl)
        assert "statistics" in result
        stats = result["statistics"]
        assert "count" in stats or "mean" in stats or "summary" in stats

    def test_empty_df_returns_empty_result(self):
        dsl = _make_simple_dsl()
        result = DSLExecutionEngine().execute(pd.DataFrame(), dsl)
        assert result["chart_data"] == {} or result["chart_data"].get("data", {}).get("labels", []) == []

    def test_histogram_output(self, sample_df):
        dsl = _make_simple_dsl(
            select=DSLSelect(metric="Lead_Time"),
            group_by=DSLGroupBy(),
            chart=DSLChart(type="histogram", bin_count=5),
        )
        result = DSLExecutionEngine().execute(sample_df, dsl)
        assert result["chart_data"]["type"] == "histogram"

    def test_time_series_line(self, sample_df):
        dsl = _make_simple_dsl(
            select=DSLSelect(metric="Lead_Time", aggregation="avg"),
            group_by=DSLGroupBy(time=DSLGroupByTime(column="Creation_Date", period="month")),
            chart=DSLChart(type="line"),
        )
        result = DSLExecutionEngine().execute(sample_df, dsl)
        assert result["chart_data"]["type"] == "line"

    def test_derived_column_integration(self, sample_df):
        dsl = _make_simple_dsl(
            derived_column=DSLDerivedColumn(
                name="rework_rate", formula="rework_size / initial_mr_size", type="ratio"
            ),
            select=DSLSelect(metric="rework_rate", aggregation="avg"),
        )
        result = DSLExecutionEngine().execute(sample_df, dsl)
        assert result["chart_data"]["type"] == "bar"
        vals = result["chart_data"]["data"]["datasets"][0]["data"]
        assert all(0 <= v <= 1 for v in vals if v is not None)

    def test_filter_integration(self, sample_df):
        dsl = _make_simple_dsl(
            filters=[DSLFilter(column="State", op="eq", value="merged")],
        )
        result = DSLExecutionEngine().execute(sample_df, dsl)
        # Only 4 merged rows → 2 authors (Alice: 3 rows, Charlie: 1 row)
        labels = result["chart_data"]["data"]["labels"]
        assert "Bob" not in labels


# ---------------------------------------------------------------------------
# ValidationLayer tests
# ---------------------------------------------------------------------------

class TestValidationLayer:
    def test_valid_dsl_passes(self, columns_metadata):
        layer = ValidationLayer()
        raw = {
            "version": "1",
            "source": {"type": "reviews"},
            "select": {"metric": "Lead_Time", "aggregation": "avg"},
            "chart": {"type": "bar"},
        }
        result = layer.validate_dsl(raw, available_columns=columns_metadata)
        assert result.valid
        assert result.errors == []

    def test_invalid_dsl_fails(self, columns_metadata):
        layer = ValidationLayer()
        raw = {"version": "1"}  # missing select and chart
        result = layer.validate_dsl(raw, available_columns=columns_metadata)
        assert not result.valid
        assert len(result.errors) > 0

    def test_python_plugin_syntax_error(self):
        layer = ValidationLayer()
        bad_code = "class X:\n  def compute(self df):\n    pass\n"  # missing comma
        result = layer.validate_python_plugin(bad_code)
        assert not result.valid
        assert any("syntax" in e.lower() or "Syntax" in e for e in result.errors)

    def test_python_plugin_valid_plugin(self, sample_df):
        layer = ValidationLayer()
        good_code = """
import pandas as pd

class TestPlugin:
    class metadata:
        code = "test_plugin"
        name = "Test"
        description = "Test plugin"
        output_columns = ["test_col"]
        required_columns = ["Lead_Time"]

    def compute(self, df):
        result = df.copy()
        result["test_col"] = result["Lead_Time"] * 2
        return result
"""
        sample_json = sample_df.to_json(orient="records")
        result = layer.validate_python_plugin(good_code, sample_df_json=sample_json, plugin_class_name="TestPlugin")
        # Should pass structural (AST) even if sandbox skips semantics
        assert result.phase in ("structural", "sandbox")
