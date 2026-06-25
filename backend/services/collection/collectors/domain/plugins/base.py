"""
MetricPlugin Base
=================
Abstract base class for all custom metric plugins in the Collection Service.

A MetricPlugin computes a new column (or a set of new columns) from the
raw review DataFrame that is produced by the GitLab/GitHub collectors.

Lifecycle:
1. LLM Service generates a metric plugin (Python class implementing MetricPlugin)
2. Validation Layer runs the plugin in sandbox against a sample
3. If valid → plugin is persisted in MetricPluginRecord model
4. MetricRegistry loads it and makes it available to DSLExecutionEngine

Example:
    class ReviewerLoadPlugin(MetricPlugin):
        @property
        def metadata(self):
            return PluginMetadata(
                code="reviewer_load",
                name="Reviewer Load",
                description="Number of MRs reviewed per reviewer.",
                output_columns=["reviewer_load"],
                required_columns=["Reviewers"],
                category="review_quality",
            )

        def compute(self, df: pd.DataFrame) -> pd.DataFrame:
            load = df["Reviewers"].value_counts().reset_index()
            load.columns = ["Reviewers", "reviewer_load"]
            return df.merge(load, on="Reviewers", how="left")
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd


@dataclass
class PluginMetadata:
    """Descriptive metadata for a MetricPlugin."""

    code: str
    """Unique machine-readable identifier (snake_case)."""

    name: str
    """Human-readable display name."""

    description: str
    """Short description shown in the metric catalogue."""

    output_columns: List[str]
    """Column names this plugin adds to the DataFrame."""

    required_columns: List[str] = field(default_factory=list)
    """Columns that must be present before this plugin can run."""

    category: str = "custom"
    """Metric category (e.g. 'review_quality', 'developer_productivity')."""

    version: str = "1.0.0"
    """Semantic version of this plugin implementation."""

    author: Optional[str] = None
    """Who created the plugin (workspace/user id)."""

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "output_columns": self.output_columns,
            "required_columns": self.required_columns,
            "category": self.category,
            "version": self.version,
            "author": self.author,
        }


class MetricPlugin(abc.ABC):
    """
    Abstract base class that every metric plugin must subclass.

    Subclasses must implement:
    - ``metadata`` property  → returns a :class:`PluginMetadata` instance
    - ``compute(df)`` method → returns the DataFrame with the new column(s) added

    The ``compute`` method MUST:
    - Never modify the input DataFrame in-place (always work on a copy)
    - Always return a DataFrame with the same number of rows as the input
    - Only add the columns declared in ``metadata.output_columns``
    - Be deterministic (same input → same output)
    """

    @property
    @abc.abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return the plugin's metadata descriptor."""

    @abc.abstractmethod
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute the metric column(s) and return an extended DataFrame.

        Parameters
        ----------
        df : pd.DataFrame
            The raw review dataset. Do NOT modify this in-place.

        Returns
        -------
        pd.DataFrame
            A new DataFrame that includes all original columns PLUS
            the columns declared in ``self.metadata.output_columns``.
        """

    def validate_input(self, df: pd.DataFrame) -> List[str]:
        """
        Check that required columns are present before calling ``compute``.

        Returns a list of missing column names (empty = all good).
        """
        return [col for col in self.metadata.required_columns if col not in df.columns]

    def safe_compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convenience wrapper: validates input then calls ``compute``.
        Raises ``ValueError`` if required columns are missing.
        """
        missing = self.validate_input(df)
        if missing:
            raise ValueError(
                f"Plugin '{self.metadata.code}' requires columns "
                f"{missing} which are not in the dataset."
            )
        return self.compute(df.copy())
