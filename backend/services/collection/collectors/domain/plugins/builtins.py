"""
Builtin Metric Plugins
======================
These plugins are always available without LLM generation.
They compute derived metrics from the standard review dataset columns.

All plugins auto-register themselves at import time via the module-level
`_register_builtins()` call at the bottom.
"""
from __future__ import annotations

import pandas as pd

from collectors.domain.plugins.base import MetricPlugin, PluginMetadata
from collectors.domain.plugins.registry import registry


class ReworkRatePlugin(MetricPlugin):
    """rework_size / initial_mr_size — bounded to [0, 1]."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            code="rework_rate",
            name="Rework Rate",
            description="Ratio of rework size to initial MR size (0 = no rework, 1 = full rewrite).",
            output_columns=["rework_rate"],
            required_columns=["rework_size", "initial_mr_size"],
            category="code_quality",
        )

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()
        denom = result["initial_mr_size"].replace(0, pd.NA)
        result["rework_rate"] = (result["rework_size"] / denom).clip(0, 1)
        return result


class ReviewCyclePlugin(MetricPlugin):
    """Days between MR creation and first review comment."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            code="review_cycle_days",
            name="Review Cycle (days)",
            description="Days from MR creation to the first review comment.",
            output_columns=["review_cycle_days"],
            required_columns=["Creation_Date", "first_review_date"],
            category="developer_productivity",
        )

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()
        t_create = pd.to_datetime(result["Creation_Date"], errors="coerce")
        t_review = pd.to_datetime(result["first_review_date"], errors="coerce")
        delta = (t_review - t_create).dt.total_seconds() / 86400
        result["review_cycle_days"] = delta.clip(lower=0)
        return result


class CommitsPerDayPlugin(MetricPlugin):
    """#Commits / Lead_Time (days) — commit velocity metric."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            code="commits_per_day",
            name="Commits per Day",
            description="Average number of commits per day of development (commits / lead_time).",
            output_columns=["commits_per_day"],
            required_columns=["#Commits", "Lead_Time"],
            category="developer_productivity",
        )

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()
        denom = result["Lead_Time"].replace(0, pd.NA)
        result["commits_per_day"] = (result["#Commits"] / denom).clip(lower=0)
        return result


class ChurnBalancePlugin(MetricPlugin):
    """churn_addition - churn_deletions — net code growth per MR."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            code="churn_balance",
            name="Churn Balance",
            description="Net code growth: lines added minus lines deleted per MR.",
            output_columns=["churn_balance"],
            required_columns=["churn_addition", "churn_deletions"],
            category="code_quality",
        )

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()
        result["churn_balance"] = result["churn_addition"] - result["churn_deletions"]
        return result


def _register_builtins() -> None:
    """Register all builtin plugins into the global registry."""
    for plugin in [
        ReworkRatePlugin(),
        ReviewCyclePlugin(),
        CommitsPerDayPlugin(),
        ChurnBalancePlugin(),
    ]:
        # overwrite=False: skip if already registered (idempotent on reimport)
        if plugin.metadata.code not in registry:
            registry.register(plugin)


_register_builtins()
