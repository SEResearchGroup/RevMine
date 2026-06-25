"""
Chart Engine
============
Converts a raw aggregation result dict into an ECharts-compatible option dict
and a matplotlib PNG (for PDF export).

The DSLExecutionEngine calls this engine as its final step.
Keeping chart formatting separate from aggregation logic means chart templates
can evolve independently of computation code.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

PALETTE = [
    "#6366f1", "#10b981", "#f59e0b", "#ef4444", "#06b6d4",
    "#8b5cf6", "#f97316", "#14b8a6", "#ec4899", "#84cc16",
    "#3b82f6", "#a855f7", "#22c55e", "#e11d48", "#0891b2",
]


class ChartEngine:
    """
    Builds an ECharts-compatible option dict from aggregated data.

    The option dict is stored in AnalysisResult.chart_data and consumed
    directly by DynamicChart.jsx (which passes it to ReactECharts).

    Note: the existing MetricsEngine produces a simpler {type, data, options}
    format that DynamicChart already adapts to ECharts internally.
    ChartEngine deliberately follows the same legacy format so the frontend
    requires zero changes for DSL-generated charts.
    """

    def build(
        self,
        chart_type: str,
        labels: List[str],
        datasets: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build the chart_data dict in the legacy format expected by DynamicChart.jsx.

        Parameters
        ----------
        chart_type : str
            One of: bar, line, area, scatter, pie, heatmap, histogram, box, multi_bar
        labels : list[str]
            X-axis labels (or category names for pie/heatmap)
        datasets : list[dict]
            Each dict has at minimum: {label: str, data: list}
        options : dict, optional
            Extra options: {title, xLabel, yLabel, stack, bin_count, ...}
        extra : dict, optional
            Extra keys merged at the top level (raw_values, scatter_x, matrix, …)
        """
        opts = options or {}
        result: Dict[str, Any] = {
            "type": chart_type,
            "data": {
                "labels": labels,
                "datasets": datasets,
            },
            "options": {
                "title": opts.get("title", ""),
                "xLabel": opts.get("xLabel", ""),
                "yLabel": opts.get("yLabel", ""),
            },
        }
        if opts.get("stack"):
            result["options"]["stack"] = True
        if opts.get("bin_count"):
            result["options"]["bin_count"] = opts["bin_count"]
        if extra:
            result["data"].update(extra)
        return result

    def build_heatmap(self, labels: List[str], matrix: List[List[float]]) -> Dict[str, Any]:
        return {
            "type": "heatmap",
            "data": {"labels": labels, "matrix": matrix},
            "options": {"title": "Correlation Matrix"},
        }

    def build_scatter(
        self,
        x_col: str,
        y_col: str,
        x_values: List[float],
        y_values: List[float],
        x_label: str = "",
        y_label: str = "",
    ) -> Dict[str, Any]:
        return {
            "type": "scatter",
            "data": {
                "labels": [f"({x:.2f}, {y:.2f})" for x, y in zip(x_values, y_values)],
                "datasets": [{"label": f"{x_col} vs {y_col}", "data": list(zip(x_values, y_values))}],
                "scatter_x": x_values,
                "scatter_y": y_values,
                "x_col": x_col,
                "y_col": y_col,
            },
            "options": {
                "title": f"{x_col} vs {y_col}",
                "xLabel": x_label or x_col,
                "yLabel": y_label or y_col,
            },
        }

    def build_histogram(
        self,
        labels: List[str],
        counts: List[int],
        raw_values: List[float],
        metric_name: str,
        bin_count: int = 30,
        x_label: str = "",
        y_label: str = "Count",
    ) -> Dict[str, Any]:
        return {
            "type": "histogram",
            "data": {
                "labels": labels,
                "datasets": [{"label": metric_name, "data": counts}],
                "raw_values": raw_values,
            },
            "options": {
                "title": f"Distribution of {metric_name}",
                "xLabel": x_label or metric_name,
                "yLabel": y_label,
                "bin_count": bin_count,
            },
        }

    def build_multi_series(
        self,
        labels: List[str],
        series: List[Dict[str, Any]],
        chart_type: str = "line",
        title: str = "",
        x_label: str = "",
        y_label: str = "",
        stack: bool = False,
    ) -> Dict[str, Any]:
        datasets = [
            {"label": s.get("label", f"Series {i}"), "data": s.get("data", [])}
            for i, s in enumerate(series)
        ]
        return self.build(
            chart_type=chart_type,
            labels=labels,
            datasets=datasets,
            options={"title": title, "xLabel": x_label, "yLabel": y_label, "stack": stack},
        )
