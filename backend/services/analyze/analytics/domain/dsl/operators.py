"""
DSL Operators
=============
Pure-pandas transformations driven by an AnalysisDSL document.
No Django ORM. No file I/O. Pure computation.

Classes:
    FilterApplier   – applies DSL filters[] to a DataFrame
    DerivedColumnBuilder – computes derived_column formulas
    Aggregator      – groups + aggregates
    StatComputer    – confidence intervals, trend lines
    Sorter          – sort + top-N
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from analytics.domain.dsl.schema import (
    AGG_TO_PANDAS,
    PERIOD_TO_PANDAS,
    AnalysisDSL,
    DSLFilter,
)


# ---------------------------------------------------------------------------
# FilterApplier
# ---------------------------------------------------------------------------

class FilterApplier:
    """Apply DSL filter expressions to a pandas DataFrame."""

    def apply(self, df: pd.DataFrame, dsl: AnalysisDSL) -> pd.DataFrame:
        result = df.copy()
        for flt in dsl.filters:
            result = self._apply_one(result, flt)
        return result

    def _apply_one(self, df: pd.DataFrame, flt: DSLFilter) -> pd.DataFrame:
        col = flt.column
        if col not in df.columns:
            return df

        series = df[col]
        op = flt.op
        val = flt.value

        if op == "eq":
            mask = series == val
        elif op == "neq":
            mask = series != val
        elif op == "gt":
            mask = pd.to_numeric(series, errors="coerce") > val
        elif op == "gte":
            mask = pd.to_numeric(series, errors="coerce") >= val
        elif op == "lt":
            mask = pd.to_numeric(series, errors="coerce") < val
        elif op == "lte":
            mask = pd.to_numeric(series, errors="coerce") <= val
        elif op == "in":
            mask = series.isin(val)
        elif op == "not_in":
            mask = ~series.isin(val)
        elif op == "between":
            lo, hi = val[0], val[1]
            numeric = pd.to_numeric(series, errors="coerce")
            if numeric.notna().any():
                mask = numeric.between(lo, hi)
            else:
                # Datetime between
                series_dt = pd.to_datetime(series, errors="coerce")
                mask = series_dt.between(pd.to_datetime(lo), pd.to_datetime(hi))
        elif op == "contains":
            mask = series.astype(str).str.contains(str(val), na=False, case=False)
        elif op == "not_null":
            mask = series.notna()
        else:
            return df

        return df[mask]


# ---------------------------------------------------------------------------
# DerivedColumnBuilder
# ---------------------------------------------------------------------------

_FORMULA_RE = re.compile(
    r"^(?P<lhs>[A-Za-z_#][A-Za-z0-9_#]*)\s*(?P<op>[+\-*/])\s*(?P<rhs>[A-Za-z_#][A-Za-z0-9_#]*)$"
)


class DerivedColumnBuilder:
    """Compute a derived column from a simple arithmetic formula."""

    def apply(self, df: pd.DataFrame, dsl: AnalysisDSL) -> pd.DataFrame:
        if dsl.derived_column is None:
            return df
        dc = dsl.derived_column
        m = _FORMULA_RE.match(dc.formula.strip())
        if not m:
            return df

        lhs_col = m.group("lhs")
        op = m.group("op")
        rhs_col = m.group("rhs")

        if lhs_col not in df.columns or rhs_col not in df.columns:
            return df

        lhs = pd.to_numeric(df[lhs_col], errors="coerce")
        rhs = pd.to_numeric(df[rhs_col], errors="coerce")

        if op == "+":
            df[dc.name] = lhs + rhs
        elif op == "-":
            df[dc.name] = lhs - rhs
        elif op == "*":
            df[dc.name] = lhs * rhs
        elif op == "/":
            df[dc.name] = lhs.where(rhs == 0, other=None) if (rhs == 0).any() else lhs / rhs.replace(0, np.nan)

        return df


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

AggResult = Dict[str, Any]


class Aggregator:
    """
    Group and aggregate the DataFrame according to the DSL.

    Returns a dict with keys:
      labels    – list of label strings (x-axis)
      values    – list[float] or list[list[float]] for multi-series
      series_names – list of series label strings
    """

    def aggregate(self, df: pd.DataFrame, dsl: AnalysisDSL) -> AggResult:
        if dsl.is_heatmap:
            return self._correlation_matrix(df, dsl)
        if dsl.is_scatter:
            return self._scatter(df, dsl)
        if dsl.is_histogram:
            return self._histogram(df, dsl)
        if dsl.is_multi_series:
            return self._multi_series(df, dsl)
        if dsl.is_time_series:
            return self._time_series(df, dsl)
        if dsl.group_by.column:
            return self._group_by_column(df, dsl)
        return self._global_agg(df, dsl)

    # --- Scatter --------------------------------------------------------

    def _scatter(self, df: pd.DataFrame, dsl: AnalysisDSL) -> AggResult:
        x_col = dsl.primary_metric
        y_col = dsl.secondary_metric
        if not x_col or not y_col:
            raise ValueError("Scatter requires 'select.metric' and 'secondary_metric'.")
        x = pd.to_numeric(df[x_col], errors="coerce")
        y = pd.to_numeric(df[y_col], errors="coerce")
        valid = x.notna() & y.notna()
        return {
            "scatter_x": x[valid].tolist(),
            "scatter_y": y[valid].tolist(),
            "x_col": x_col,
            "y_col": y_col,
            "labels": [],
            "values": [],
            "series_names": [f"{x_col} vs {y_col}"],
        }

    # --- Histogram ------------------------------------------------------

    def _histogram(self, df: pd.DataFrame, dsl: AnalysisDSL) -> AggResult:
        col = dsl.primary_metric
        if not col:
            raise ValueError("Histogram requires 'select.metric'.")
        vals = pd.to_numeric(df[col], errors="coerce").dropna()
        bin_count = dsl.chart.bin_count or 30
        counts, edges = np.histogram(vals, bins=bin_count)
        labels = [f"{edges[i]:.1f}–{edges[i+1]:.1f}" for i in range(len(counts))]
        return {
            "labels": labels,
            "values": counts.tolist(),
            "raw_values": vals.tolist(),
            "series_names": [col],
        }

    # --- Correlation heatmap -------------------------------------------

    def _correlation_matrix(self, df: pd.DataFrame, dsl: AnalysisDSL) -> AggResult:
        cols = dsl.select.metrics
        numeric_df = df[cols].apply(pd.to_numeric, errors="coerce")
        corr = numeric_df.corr(method="pearson")
        return {
            "labels": cols,
            "matrix": corr.values.tolist(),
            "values": [],
            "series_names": cols,
        }

    # --- Time series ----------------------------------------------------

    def _time_series(self, df: pd.DataFrame, dsl: AnalysisDSL) -> AggResult:
        date_col = dsl.group_by.time_column
        period = dsl.group_by.time_period or "month"
        pandas_freq = PERIOD_TO_PANDAS.get(period, "M")
        metric_col = dsl.primary_metric
        agg_method = AGG_TO_PANDAS.get(dsl.select.aggregation, "mean")

        df_c = df.copy()
        df_c[date_col] = pd.to_datetime(df_c[date_col], errors="coerce")
        df_c = df_c.dropna(subset=[date_col])
        df_c["_period"] = df_c[date_col].dt.to_period(pandas_freq)

        if metric_col and metric_col in df_c.columns:
            df_c[metric_col] = pd.to_numeric(df_c[metric_col], errors="coerce")
            if callable(agg_method):
                result = df_c.groupby("_period")[metric_col].apply(agg_method)
            else:
                result = df_c.groupby("_period")[metric_col].agg(agg_method)
        else:
            result = df_c.groupby("_period").size()
            metric_col = "count"

        result = result.sort_index()
        labels = [_format_period(p) for p in result.index]
        values = [_safe_float(v) for v in result.values]

        return {"labels": labels, "values": values, "series_names": [metric_col]}

    # --- Group-by column ------------------------------------------------

    def _group_by_column(self, df: pd.DataFrame, dsl: AnalysisDSL) -> AggResult:
        group_col = dsl.group_by.column
        metric_col = dsl.primary_metric
        agg_name = dsl.select.aggregation
        agg_method = AGG_TO_PANDAS.get(agg_name, "mean")

        df_c = df.copy()
        df_c[group_col] = df_c[group_col].astype(str)

        if metric_col and metric_col in df_c.columns and agg_name != "count":
            df_c[metric_col] = pd.to_numeric(df_c[metric_col], errors="coerce")
            if callable(agg_method):
                result = df_c.groupby(group_col)[metric_col].apply(agg_method)
            else:
                result = df_c.groupby(group_col)[metric_col].agg(agg_method)
        else:
            result = df_c.groupby(group_col).size()
            metric_col = "count"

        labels = [str(l) for l in result.index]
        values = [_safe_float(v) for v in result.values]
        return {"labels": labels, "values": values, "series_names": [metric_col]}

    # --- Global aggregation (no group) ----------------------------------

    def _global_agg(self, df: pd.DataFrame, dsl: AnalysisDSL) -> AggResult:
        metric_col = dsl.primary_metric
        agg_name = dsl.select.aggregation
        agg_method = AGG_TO_PANDAS.get(agg_name, "mean")

        if not metric_col or metric_col not in df.columns:
            raise ValueError(f"Column '{metric_col}' not found in dataset.")

        series = pd.to_numeric(df[metric_col], errors="coerce").dropna()
        if callable(agg_method):
            value = agg_method(series)
        else:
            value = getattr(series, agg_method)()

        return {
            "labels": [f"{metric_col} ({agg_name})"],
            "values": [_safe_float(value)],
            "series_names": [metric_col],
        }

    # --- Multi-series ---------------------------------------------------

    def _multi_series(self, df: pd.DataFrame, dsl: AnalysisDSL) -> AggResult:
        group_col = dsl.group_by.column
        time_col = dsl.group_by.time_column
        period = dsl.group_by.time_period or "month"
        pandas_freq = PERIOD_TO_PANDAS.get(period, "M")

        df_c = df.copy()
        all_values: List[List[float]] = []
        all_labels: Optional[List[str]] = None
        series_names: List[str] = []

        for serie in dsl.series:
            agg_method = AGG_TO_PANDAS.get(serie.aggregation, "mean")
            df_c[serie.metric] = pd.to_numeric(df_c[serie.metric], errors="coerce")

            if time_col:
                df_c[time_col] = pd.to_datetime(df_c[time_col], errors="coerce")
                df_c["_period"] = df_c[time_col].dt.to_period(pandas_freq)
                if callable(agg_method):
                    result = df_c.groupby("_period")[serie.metric].apply(agg_method)
                else:
                    result = df_c.groupby("_period")[serie.metric].agg(agg_method)
                result = result.sort_index()
                if all_labels is None:
                    all_labels = [_format_period(p) for p in result.index]
            elif group_col:
                if callable(agg_method):
                    result = df_c.groupby(group_col)[serie.metric].apply(agg_method)
                else:
                    result = df_c.groupby(group_col)[serie.metric].agg(agg_method)
                if all_labels is None:
                    all_labels = [str(l) for l in result.index]
            else:
                series_val = getattr(
                    pd.to_numeric(df_c[serie.metric], errors="coerce").dropna(),
                    agg_method if isinstance(agg_method, str) else "mean",
                )()
                all_values.append([_safe_float(series_val)])
                series_names.append(serie.label or serie.metric)
                continue

            all_values.append([_safe_float(v) for v in result.values])
            series_names.append(serie.label or serie.metric)

        return {
            "labels": all_labels or [],
            "values": all_values,
            "series_names": series_names,
            "is_multi": True,
        }


# ---------------------------------------------------------------------------
# StatComputer
# ---------------------------------------------------------------------------

class StatComputer:
    """Compute optional statistics: confidence intervals, trend line, summary stats."""

    def compute(self, df: pd.DataFrame, agg_result: AggResult, dsl: AnalysisDSL) -> Dict[str, Any]:
        stats: Dict[str, Any] = {}

        metric_col = dsl.primary_metric
        if metric_col and metric_col in df.columns:
            series = pd.to_numeric(df[metric_col], errors="coerce").dropna()
            if len(series) > 0:
                stats.update({
                    "count": int(len(series)),
                    "mean": _safe_float(series.mean()),
                    "median": _safe_float(series.median()),
                    "std": _safe_float(series.std()),
                    "min": _safe_float(series.min()),
                    "max": _safe_float(series.max()),
                    "p25": _safe_float(series.quantile(0.25)),
                    "p75": _safe_float(series.quantile(0.75)),
                    "p95": _safe_float(series.quantile(0.95)),
                })

        # Confidence intervals per group
        ci = dsl.chart.confidence_interval
        if ci and dsl.group_by.column and metric_col:
            stats["confidence_intervals"] = self._compute_ci(df, dsl, ci)

        # Trend line parameters for time series
        if dsl.chart.trend_line and agg_result.get("values"):
            values = agg_result["values"]
            if values and not isinstance(values[0], list):
                stats["trend"] = self._linear_trend(values)

        return stats

    def _compute_ci(self, df: pd.DataFrame, dsl: AnalysisDSL, ci_pct: int) -> Dict[str, Any]:
        try:
            from scipy import stats as scipy_stats
        except ImportError:
            return {}

        alpha = 1 - ci_pct / 100
        group_col = dsl.group_by.column
        metric_col = dsl.primary_metric
        result = {}
        for group, group_df in df.groupby(group_col):
            vals = pd.to_numeric(group_df[metric_col], errors="coerce").dropna()
            n = len(vals)
            if n < 2:
                continue
            mean = vals.mean()
            se = vals.std() / np.sqrt(n)
            t_crit = scipy_stats.t.ppf(1 - alpha / 2, df=n - 1)
            margin = t_crit * se
            result[str(group)] = {
                "mean": _safe_float(mean),
                "ci_lower": _safe_float(mean - margin),
                "ci_upper": _safe_float(mean + margin),
                "n": n,
            }
        return result

    def _linear_trend(self, values: List[float]) -> Dict[str, Any]:
        try:
            from scipy import stats as scipy_stats
            x = np.arange(len(values))
            y = np.array([v if v is not None else np.nan for v in values], dtype=float)
            valid = ~np.isnan(y)
            if valid.sum() < 2:
                return {}
            slope, intercept, r_value, p_value, _ = scipy_stats.linregress(x[valid], y[valid])
            trend_values = (slope * x + intercept).tolist()
            return {
                "slope": _safe_float(slope),
                "intercept": _safe_float(intercept),
                "r_squared": _safe_float(r_value ** 2),
                "p_value": _safe_float(p_value),
                "trend_values": [_safe_float(v) for v in trend_values],
            }
        except Exception:
            return {}


# ---------------------------------------------------------------------------
# Sorter
# ---------------------------------------------------------------------------

class Sorter:
    """Apply sort + limit to aggregation result."""

    def apply(self, agg_result: AggResult, dsl: AnalysisDSL) -> AggResult:
        values = agg_result.get("values", [])
        labels = agg_result.get("labels", [])

        if not values or not labels or isinstance(values[0], list):
            return agg_result  # Multi-series or empty; skip

        if dsl.sort.by == "value":
            paired = sorted(zip(values, labels), key=lambda x: x[0] or 0,
                            reverse=(dsl.sort.order == "desc"))
        else:
            paired = sorted(zip(values, labels), key=lambda x: str(x[1]),
                            reverse=(dsl.sort.order == "desc"))

        if dsl.limit:
            paired = paired[:dsl.limit]

        if paired:
            agg_result["values"], agg_result["labels"] = zip(*paired)
            agg_result["values"] = list(agg_result["values"])
            agg_result["labels"] = list(agg_result["labels"])

        return agg_result


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _safe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
        if np.isnan(f) or np.isinf(f):
            return None
        return round(f, 4)
    except (TypeError, ValueError):
        return None


def _format_period(p: Any) -> str:
    try:
        return p.to_timestamp().strftime("%Y-%m-%d")
    except Exception:
        return str(p)
