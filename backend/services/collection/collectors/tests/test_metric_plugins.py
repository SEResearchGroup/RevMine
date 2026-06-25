"""
Unit tests for the Metric Plugin system (Collection Service).

Tests cover:
- MetricPlugin base class contract
- MetricRegistry: register, unregister, get, apply
- Builtin plugins: ReworkRate, ReviewCycle, CommitsPerDay, ChurnBalance
"""
from __future__ import annotations

import pytest
import pandas as pd
import numpy as np

from collectors.domain.plugins.base import MetricPlugin, PluginMetadata
from collectors.domain.plugins.registry import MetricRegistry
from collectors.domain.plugins.builtins import (
    ReworkRatePlugin,
    ReviewCyclePlugin,
    CommitsPerDayPlugin,
    ChurnBalancePlugin,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def review_df():
    """Minimal review dataset with all columns required by builtin plugins."""
    return pd.DataFrame({
        "Author":              ["Alice", "Bob", "Charlie"],
        "rework_size":         [10, 20, 0],
        "initial_mr_size":     [100, 100, 50],
        "Creation_Date":       pd.to_datetime(["2024-01-01", "2024-01-05", "2024-01-10"]),
        "first_review_date":   pd.to_datetime(["2024-01-03", "2024-01-07", "2024-01-11"]),
        "#Commits":            [3, 5, 1],
        "Lead_Time":           [5.0, 10.0, 2.0],
        "churn_addition":      [100, 200, 50],
        "churn_deletions":     [20, 50, 10],
    })


@pytest.fixture
def fresh_registry():
    """A clean MetricRegistry for each test (not the global singleton)."""
    return MetricRegistry()


# ---------------------------------------------------------------------------
# MetricPlugin contract tests
# ---------------------------------------------------------------------------

class TestMetricPluginContract:
    def test_safe_compute_validates_required_columns(self, review_df):
        plugin = ReworkRatePlugin()
        # Drop a required column
        df_missing = review_df.drop(columns=["initial_mr_size"])
        with pytest.raises(ValueError, match="requires columns"):
            plugin.safe_compute(df_missing)

    def test_safe_compute_does_not_mutate_input(self, review_df):
        plugin = ReworkRatePlugin()
        original_cols = list(review_df.columns)
        plugin.safe_compute(review_df)
        assert list(review_df.columns) == original_cols

    def test_safe_compute_returns_same_row_count(self, review_df):
        plugin = ReworkRatePlugin()
        result = plugin.safe_compute(review_df)
        assert len(result) == len(review_df)

    def test_validate_input_returns_missing_cols(self, review_df):
        plugin = ReworkRatePlugin()
        missing = plugin.validate_input(review_df.drop(columns=["rework_size"]))
        assert "rework_size" in missing


# ---------------------------------------------------------------------------
# MetricRegistry tests
# ---------------------------------------------------------------------------

class TestMetricRegistry:
    def test_register_and_get(self, fresh_registry):
        plugin = ReworkRatePlugin()
        fresh_registry.register(plugin)
        assert "rework_rate" in fresh_registry
        assert fresh_registry.get("rework_rate") is plugin

    def test_register_duplicate_raises(self, fresh_registry):
        fresh_registry.register(ReworkRatePlugin())
        with pytest.raises(ValueError, match="already registered"):
            fresh_registry.register(ReworkRatePlugin())

    def test_register_overwrite(self, fresh_registry):
        fresh_registry.register(ReworkRatePlugin())
        # Should not raise
        fresh_registry.register(ReworkRatePlugin(), overwrite=True)

    def test_unregister(self, fresh_registry):
        fresh_registry.register(ReworkRatePlugin())
        existed = fresh_registry.unregister("rework_rate")
        assert existed
        assert "rework_rate" not in fresh_registry

    def test_unregister_nonexistent_returns_false(self, fresh_registry):
        assert fresh_registry.unregister("no_such_plugin") is False

    def test_list_returns_metadata(self, fresh_registry):
        fresh_registry.register(ReworkRatePlugin())
        fresh_registry.register(CommitsPerDayPlugin())
        metas = fresh_registry.list()
        codes = [m.code for m in metas]
        assert "rework_rate" in codes
        assert "commits_per_day" in codes

    def test_codes_returns_list(self, fresh_registry):
        fresh_registry.register(ReworkRatePlugin())
        assert "rework_rate" in fresh_registry.codes()

    def test_apply_returns_df_with_new_col(self, fresh_registry, review_df):
        fresh_registry.register(ReworkRatePlugin())
        result = fresh_registry.apply("rework_rate", review_df)
        assert "rework_rate" in result.columns

    def test_apply_unknown_code_raises(self, fresh_registry, review_df):
        with pytest.raises(KeyError):
            fresh_registry.apply("no_such", review_df)

    def test_apply_all(self, fresh_registry, review_df):
        fresh_registry.register(ReworkRatePlugin())
        fresh_registry.register(ChurnBalancePlugin())
        result = fresh_registry.apply_all(review_df)
        assert "rework_rate" in result.columns
        assert "churn_balance" in result.columns

    def test_apply_all_skips_failing_plugin(self, fresh_registry, review_df):
        fresh_registry.register(ReworkRatePlugin())
        # Drop required column so ReworkRatePlugin will fail
        df_broken = review_df.drop(columns=["initial_mr_size"])
        # Should not raise — just skip
        result = fresh_registry.apply_all(df_broken)
        assert "rework_rate" not in result.columns

    def test_apply_for_columns(self, fresh_registry, review_df):
        fresh_registry.register(ReworkRatePlugin())
        fresh_registry.register(ChurnBalancePlugin())
        # Only request rework_rate — churn_balance should NOT be computed
        result = fresh_registry.apply_for_columns(review_df, needed_columns=["rework_rate"])
        assert "rework_rate" in result.columns


# ---------------------------------------------------------------------------
# Builtin plugin tests
# ---------------------------------------------------------------------------

class TestReworkRatePlugin:
    def test_output_bounded_0_1(self, review_df):
        result = ReworkRatePlugin().safe_compute(review_df)
        assert "rework_rate" in result.columns
        vals = result["rework_rate"].dropna()
        assert (vals >= 0).all() and (vals <= 1).all()

    def test_zero_denominator_produces_na(self, review_df):
        df = review_df.copy()
        df.loc[0, "initial_mr_size"] = 0
        result = ReworkRatePlugin().safe_compute(df)
        assert pd.isna(result.loc[0, "rework_rate"])

    def test_zero_rework(self, review_df):
        result = ReworkRatePlugin().safe_compute(review_df)
        charlie_rate = result.loc[result.index[2], "rework_rate"]
        assert charlie_rate == pytest.approx(0.0)


class TestReviewCyclePlugin:
    def test_positive_cycle_days(self, review_df):
        result = ReviewCyclePlugin().safe_compute(review_df)
        assert "review_cycle_days" in result.columns
        assert (result["review_cycle_days"] >= 0).all()

    def test_cycle_is_2_days(self, review_df):
        # Alice: Jan 1 → Jan 3 = 2 days
        result = ReviewCyclePlugin().safe_compute(review_df)
        assert result.loc[result.index[0], "review_cycle_days"] == pytest.approx(2.0)


class TestCommitsPerDayPlugin:
    def test_positive_values(self, review_df):
        result = CommitsPerDayPlugin().safe_compute(review_df)
        assert "commits_per_day" in result.columns
        assert (result["commits_per_day"] >= 0).all()

    def test_zero_lead_time_produces_na(self, review_df):
        df = review_df.copy()
        df.loc[0, "Lead_Time"] = 0
        result = CommitsPerDayPlugin().safe_compute(df)
        assert pd.isna(result.loc[0, "commits_per_day"])


class TestChurnBalancePlugin:
    def test_balance_is_addition_minus_deletions(self, review_df):
        result = ChurnBalancePlugin().safe_compute(review_df)
        assert "churn_balance" in result.columns
        expected = review_df["churn_addition"] - review_df["churn_deletions"]
        pd.testing.assert_series_equal(
            result["churn_balance"], expected, check_names=False
        )

    def test_negative_balance_possible(self):
        df = pd.DataFrame({
            "churn_addition":  [10],
            "churn_deletions": [50],
        })
        result = ChurnBalancePlugin().safe_compute(df)
        assert result.loc[0, "churn_balance"] == -40
