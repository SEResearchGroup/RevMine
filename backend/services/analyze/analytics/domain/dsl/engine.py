"""
DSL Execution Engine
====================
Orchestrates the full pipeline from a validated AnalysisDSL to a result dict
compatible with the existing chart_data format consumed by DynamicChart.jsx.

Pipeline:
    DataFrame
        → DerivedColumnBuilder (optional new column)
        → FilterApplier
        → Aggregator   (group/time-series/scatter/histogram/heatmap)
        → StatComputer (confidence intervals, trend line, summary stats)
        → Sorter       (sort + top-N)
        → ChartEngine  (format for frontend)
"""
from __future__ import annotations

import logging
from typing import Any, Dict

import pandas as pd

from analytics.domain.dsl.operators import (
    Aggregator,
    DerivedColumnBuilder,
    FilterApplier,
    Sorter,
    StatComputer,
)
from analytics.domain.dsl.schema import AnalysisDSL

logger = logging.getLogger(__name__)


class DSLExecutionEngine:
    """
    Execute an AnalysisDSL on a pandas DataFrame.

    Returns a dict with the same structure as MetricsEngine methods:
    {
        'chart_data':  dict   – chart.js-like payload consumed by DynamicChart.jsx
        'chart_image': str    – base64 matplotlib PNG (optional, for PDF export)
        'statistics':  dict   – summary statistics
        'dsl':         dict   – the DSL document that produced this result
    }
    """

    def __init__(self):
        self._filter_applier = FilterApplier()
        self._derived_builder = DerivedColumnBuilder()
        self._aggregator = Aggregator()
        self._stat_computer = StatComputer()
        self._sorter = Sorter()

    def execute(self, df: pd.DataFrame, dsl: AnalysisDSL) -> Dict[str, Any]:
        # 1. Compute derived column (if declared)
        df = self._derived_builder.apply(df, dsl)

        # 2. Apply filters
        df = self._filter_applier.apply(df, dsl)

        if len(df) == 0:
            return self._empty_result(dsl)

        # 3. Aggregate
        agg_result = self._aggregator.aggregate(df, dsl)

        # 4. Sort + limit (only for non-multi-series flat results)
        agg_result = self._sorter.apply(agg_result, dsl)

        # 5. Statistics
        statistics = self._stat_computer.compute(df, agg_result, dsl)

        # 6. Build chart_data
        chart_data = self._build_chart_data(agg_result, dsl)

        # 7. Generate matplotlib image for export (best-effort)
        chart_image = self._generate_image(agg_result, dsl)

        return {
            "chart_data": chart_data,
            "chart_image": chart_image,
            "statistics": statistics,
            "dsl": dsl.to_dict(),
        }

    # ------------------------------------------------------------------
    # chart_data builder — produces format consumed by DynamicChart.jsx
    # ------------------------------------------------------------------

    def _build_chart_data(self, agg: Dict[str, Any], dsl: AnalysisDSL) -> Dict[str, Any]:
        chart_type = dsl.chart.type
        labels = agg.get("labels", [])
        values = agg.get("values", [])
        series_names = agg.get("series_names", [dsl.primary_metric or "value"])

        # Heatmap
        if dsl.is_heatmap:
            return {
                "type": "heatmap",
                "data": {
                    "labels": labels,
                    "matrix": agg.get("matrix", []),
                },
                "options": {"title": "Correlation Matrix"},
            }

        # Scatter
        if dsl.is_scatter:
            x_col = agg.get("x_col", "")
            y_col = agg.get("y_col", "")
            scatter_x = agg.get("scatter_x", [])
            scatter_y = agg.get("scatter_y", [])
            return {
                "type": "scatter",
                "data": {
                    "labels": [f"({x:.2f}, {y:.2f})" for x, y in zip(scatter_x, scatter_y)],
                    "datasets": [{
                        "label": f"{x_col} vs {y_col}",
                        "data": [{"x": x, "y": y} for x, y in zip(scatter_x, scatter_y)],
                    }],
                    "scatter_x": scatter_x,
                    "scatter_y": scatter_y,
                    "x_col": x_col,
                    "y_col": y_col,
                },
                "options": {
                    "title": f"{x_col} vs {y_col}",
                    "xLabel": dsl.chart.x_label or x_col,
                    "yLabel": dsl.chart.y_label or y_col,
                },
            }

        # Histogram
        if dsl.is_histogram:
            return {
                "type": "histogram",
                "data": {
                    "labels": labels,
                    "datasets": [{"label": series_names[0] if series_names else "count", "data": values}],
                    "raw_values": agg.get("raw_values", []),
                },
                "options": {
                    "title": f"Distribution of {series_names[0] if series_names else ''}",
                    "xLabel": dsl.chart.x_label or (series_names[0] if series_names else ""),
                    "yLabel": dsl.chart.y_label or "Count",
                    "bin_count": dsl.chart.bin_count or 30,
                },
            }

        # Multi-series
        if dsl.is_multi_series:
            multi_values = values if isinstance(values, list) and values and isinstance(values[0], list) else [values]
            datasets = [
                {"label": name, "data": vals}
                for name, vals in zip(series_names, multi_values)
            ]
            return {
                "type": chart_type,
                "data": {"labels": labels, "datasets": datasets},
                "options": {
                    "title": " vs ".join(series_names),
                    "xLabel": dsl.chart.x_label or "",
                    "yLabel": dsl.chart.y_label or "",
                    "stack": dsl.chart.stack,
                },
            }

        # Single-series (bar, line, area, pie)
        title = self._build_title(dsl)
        return {
            "type": chart_type,
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": series_names[0] if series_names else "value",
                    "data": values,
                }],
            },
            "options": {
                "title": title,
                "xLabel": dsl.chart.x_label or (dsl.group_by.column or dsl.group_by.time_column or ""),
                "yLabel": dsl.chart.y_label or (series_names[0] if series_names else "value"),
            },
        }

    def _build_title(self, dsl: AnalysisDSL) -> str:
        metric = dsl.primary_metric or ""
        agg = dsl.select.aggregation
        if dsl.group_by.column:
            return f"{metric} ({agg}) by {dsl.group_by.column}"
        if dsl.group_by.time_column:
            return f"{metric} ({agg}) over {dsl.group_by.time_period or 'time'}"
        return f"{metric} ({agg})"

    # ------------------------------------------------------------------
    # Matplotlib image (for PDF export)
    # ------------------------------------------------------------------

    def _generate_image(self, agg: Dict[str, Any], dsl: AnalysisDSL) -> str:
        try:
            import base64
            import io

            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            labels = agg.get("labels", [])
            values = agg.get("values", [])
            chart_type = dsl.chart.type

            if not labels and not values:
                return ""

            fig, ax = plt.subplots(figsize=(12, 6))

            if dsl.is_heatmap:
                import seaborn as sns
                matrix = agg.get("matrix", [])
                if matrix:
                    import numpy as np
                    im = ax.imshow(np.array(matrix), cmap="coolwarm", vmin=-1, vmax=1)
                    ax.set_xticks(range(len(labels)))
                    ax.set_yticks(range(len(labels)))
                    ax.set_xticklabels(labels, rotation=45, ha="right")
                    ax.set_yticklabels(labels)
                    plt.colorbar(im, ax=ax)
                    ax.set_title("Correlation Matrix")
            elif dsl.is_scatter:
                x = agg.get("scatter_x", [])
                y = agg.get("scatter_y", [])
                ax.scatter(x, y, alpha=0.6)
                ax.set_xlabel(agg.get("x_col", ""))
                ax.set_ylabel(agg.get("y_col", ""))
            elif dsl.is_histogram:
                raw = agg.get("raw_values", [])
                if raw:
                    ax.hist(raw, bins=dsl.chart.bin_count or 30, color="steelblue", edgecolor="white")
            elif dsl.is_multi_series:
                x = range(len(labels))
                for name, vals in zip(agg.get("series_names", []), values if isinstance(values[0], list) else [values]):
                    ax.plot(list(x), vals, marker="o", label=name) if chart_type in ("line", "area") else ax.bar(list(x), vals, label=name)
                ax.legend()
                ax.set_xticks(list(x))
                ax.set_xticklabels(labels, rotation=45, ha="right")
            else:
                x = range(len(labels))
                if chart_type in ("line", "area"):
                    ax.plot(list(x), values, marker="o", linewidth=2)
                    if dsl.chart.trend_line:
                        from analytics.domain.dsl.operators import StatComputer
                        sc = StatComputer()
                        trend = sc._linear_trend(values)
                        if trend.get("trend_values"):
                            ax.plot(list(x), trend["trend_values"], "--", color="red", alpha=0.6, label="Trend")
                elif chart_type == "pie":
                    ax.pie(values, labels=labels, autopct="%1.1f%%")
                else:
                    ax.bar(list(x), values, color="steelblue")
                if chart_type != "pie":
                    ax.set_xticks(list(x))
                    ax.set_xticklabels(labels, rotation=45, ha="right")

            ax.set_title(self._build_title(dsl))
            ax.grid(axis="y", alpha=0.3)
            plt.tight_layout()

            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
            buf.seek(0)
            img = base64.b64encode(buf.read()).decode("utf-8")
            plt.close(fig)
            return f"data:image/png;base64,{img}"

        except Exception as exc:
            logger.warning("Could not generate matplotlib image: %s", exc)
            return ""

    def _empty_result(self, dsl: AnalysisDSL) -> Dict[str, Any]:
        return {
            "chart_data": {
                "type": dsl.chart.type,
                "data": {"labels": [], "datasets": [{"label": "No data", "data": []}]},
                "options": {"title": "No data after filtering"},
            },
            "chart_image": "",
            "statistics": {"count": 0, "message": "No rows matched the applied filters."},
            "dsl": dsl.to_dict(),
        }
