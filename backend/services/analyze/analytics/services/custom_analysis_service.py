"""
Custom Analysis Service
=======================
Orchestrates the full DSL-First pipeline:

1. Receive a natural-language query + dataset
2. Call LLM Service to generate DSL JSON
3. Validate DSL against dataset columns
4. Execute via DSLExecutionEngine
5. Persist AnalysisResult
6. Return structured response

Also handles:
- Direct DSL execution (skipping LLM)
- Python code execution (for complex metrics beyond DSL)
- Smart preview (hybrid: predefined → DSL → Python)
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests
from django.conf import settings
from django.utils import timezone

from analytics.domain.dsl import DSLExecutionEngine, DSLValidator
from analytics.domain.dsl.schema import AnalysisDSL
from analytics.domain.dsl.validator import DSLValidationError
from analytics.models import Analysis, AnalysisResult, Dataset
from analytics.services.dataset_service import DatasetService

logger = logging.getLogger(__name__)

LLM_SERVICE_URL = getattr(settings, "LLM_SERVICE_URL", "http://llm-service:8004")
LLM_DEFAULT_BACKEND = getattr(settings, "LLM_DEFAULT_BACKEND", "openrouter")


class CustomAnalysisService:
    """End-to-end custom analysis pipeline (DSL + Python fallback)."""

    def __init__(self):
        self._dataset_service = DatasetService()
        self._engine = DSLExecutionEngine()

    # ------------------------------------------------------------------
    # Main entry points
    # ------------------------------------------------------------------

    def run_from_nl_query(
        self,
        dataset: Dataset,
        nl_query: str,
        model: Optional[str] = None,
        backend: str = LLM_DEFAULT_BACKEND,
        custom_label: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Full NL → DSL → Execute pipeline."""
        columns_metadata = dataset.columns_metadata or {}
        column_names = list(columns_metadata.keys())

        dsl_raw = self._generate_dsl(nl_query, column_names, model=model, backend=backend)
        dsl_raw["version"] = dsl_raw.get("version", "1")
        dsl_raw.setdefault("source", {"type": "reviews"})
        dsl_raw = self._fix_histogram_as_groupby(dsl_raw, columns_metadata)

        validator = DSLValidator(available_columns=columns_metadata)
        try:
            dsl = validator.parse(dsl_raw)
        except DSLValidationError as exc:
            return {
                "status": "dsl_error",
                "error": str(exc),
                "field": exc.field,
                "suggestion": exc.suggestion,
                "dsl_raw": dsl_raw,
            }

        return self._execute_and_persist(dataset, dsl, nl_query=nl_query, custom_label=custom_label)

    def run_from_dsl(
        self,
        dataset: Dataset,
        dsl_raw: Dict[str, Any],
        nl_query: Optional[str] = None,
        custom_label: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Direct DSL execution (skip LLM generation)."""
        columns_metadata = dataset.columns_metadata or {}
        dsl_raw = self._fix_histogram_as_groupby(dsl_raw, columns_metadata)
        validator = DSLValidator(available_columns=columns_metadata)
        try:
            dsl = validator.parse(dsl_raw)
        except DSLValidationError as exc:
            return {
                "status": "dsl_error",
                "error": str(exc),
                "field": exc.field,
                "suggestion": exc.suggestion,
                "dsl_raw": dsl_raw,
            }
        return self._execute_and_persist(dataset, dsl, nl_query=nl_query, custom_label=custom_label)

    def run_python_analysis(
        self,
        dataset: Dataset,
        python_code: str,
        nl_query: Optional[str] = None,
        custom_label: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute Python code on the dataset and persist the result."""
        import pandas as pd
        import numpy as np

        df = self._dataset_service.load_dataframe(dataset)

        # Parse datetime columns
        for col, meta in (dataset.columns_metadata or {}).items():
            if isinstance(meta, dict) and meta.get("type") in ("datetime", "datetime_string"):
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors="coerce")

        exec_result = self._safe_exec_python(python_code, df)
        if "error" in exec_result:
            return {
                "status": "python_error",
                "error": exec_result["error"],
                "code": python_code,
            }

        result_data = exec_result.get("result_data", [])
        chart_type = exec_result.get("chart_type", "bar")
        statistics = exec_result.get("statistics", {})

        # Convert result_data → chart_data (Chart.js compatible)
        chart_data = self._result_data_to_chart(result_data, chart_type, nl_query)

        from analytics.domain.metrics.metrics_engine import MetricsEngine
        engine = MetricsEngine()
        chart_data = engine._sanitize_value(chart_data)
        statistics = engine._sanitize_value(statistics)

        analysis = Analysis.objects.create(
            dataset=dataset,
            metric_code="custom_python",
            chart_type=chart_type,
            config={"python_code": python_code},
            dsl_config={},
            nl_query=nl_query or "",
            custom_label=custom_label or (nl_query[:100] if nl_query else "Python Analysis"),
            is_custom=True,
            status="completed",
            completed_at=timezone.now(),
        )

        AnalysisResult.objects.create(
            analysis=analysis,
            chart_data=chart_data,
            chart_image="",
            statistics=statistics,
        )

        return {
            "status": "completed",
            "analysis_id": str(analysis.id),
            "dataset_id": str(dataset.id),
            "mode": "python_code",
            "nl_query": nl_query,
            "chart_type": chart_type,
            "chart_data": chart_data,
            "statistics": statistics,
            "generated_at": analysis.completed_at.isoformat(),
        }

    def preview_nl_query(
        self,
        dataset: Dataset,
        nl_query: str,
        model: Optional[str] = None,
        backend: str = LLM_DEFAULT_BACKEND,
    ) -> Dict[str, Any]:
        """
        Generate DSL from NL without executing it.
        Returns {mode: "custom_dsl", dsl_raw, dsl_plan} or {mode: "python_code", code}.
        """
        columns_metadata = dataset.columns_metadata or {}
        column_names = list(columns_metadata.keys())

        dsl_raw = self._generate_dsl(nl_query, column_names, model=model, backend=backend)
        dsl_raw["version"] = dsl_raw.get("version", "1")
        dsl_raw.setdefault("source", {"type": "reviews"})
        dsl_raw = self._fix_histogram_as_groupby(dsl_raw, columns_metadata)

        # DSL insufficient → escalate to Python
        if dsl_raw.get("error") == "dsl_insufficient":
            python_code = self._generate_python_code(nl_query, column_names, model=model, backend=backend)
            return {
                "mode": "python_code",
                "code": python_code,
                "reason": dsl_raw.get("reason", ""),
            }

        # DSL error (column missing etc.)
        if "error" in dsl_raw:
            return {
                "mode": "dsl_error",
                "error": dsl_raw.get("user_message") or dsl_raw.get("reason") or str(dsl_raw.get("error")),
                "dsl_raw": dsl_raw,
            }

        # Validate DSL
        validator = DSLValidator(available_columns=columns_metadata)
        try:
            dsl = validator.parse(dsl_raw)
        except DSLValidationError as exc:
            return {
                "mode": "dsl_error",
                "error": str(exc),
                "field": exc.field,
                "suggestion": exc.suggestion,
                "dsl_raw": dsl_raw,
            }

        return {
            "mode": "custom_dsl",
            "dsl_raw": dsl_raw,
            "dsl_plan": self._dsl_to_plan(dsl),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fix_histogram_as_groupby(dsl_raw: Dict[str, Any], columns_metadata: Dict) -> Dict[str, Any]:
        chart_type = dsl_raw.get("chart", {}).get("type")
        if chart_type != "histogram":
            return dsl_raw

        group_col = dsl_raw.get("group_by", {}).get("column")
        if group_col:
            col_meta = columns_metadata.get(group_col, {})
            col_type = col_meta.get("type", "") if isinstance(col_meta, dict) else col_meta
            if col_type == "categorical":
                new_dsl = {**dsl_raw}
                new_dsl["chart"] = {**dsl_raw.get("chart", {}), "type": "bar"}
                return new_dsl
            return dsl_raw

        filters = dsl_raw.get("filters", [])
        for flt in filters:
            col = flt.get("column", "")
            col_meta = columns_metadata.get(col, {})
            col_type = col_meta.get("type", "") if isinstance(col_meta, dict) else col_meta
            if col_type == "categorical":
                remaining = [f for f in filters if f is not flt]
                new_dsl = {**dsl_raw}
                new_dsl["chart"] = {**dsl_raw.get("chart", {}), "type": "bar"}
                new_dsl["group_by"] = {"column": col}
                if remaining:
                    new_dsl["filters"] = remaining
                else:
                    new_dsl.pop("filters", None)
                return new_dsl

        return dsl_raw

    def _generate_dsl(
        self,
        nl_query: str,
        column_names: list,
        model: Optional[str] = None,
        backend: str = "openrouter",
    ) -> Dict[str, Any]:
        endpoint = f"{LLM_SERVICE_URL}/dsl/generate"
        payload: Dict[str, Any] = {
            "user_message": nl_query,
            "available_columns": column_names,
            "backend": backend,
        }
        if model:
            payload["model"] = model

        try:
            resp = requests.post(endpoint, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            dsl = data.get("dsl") or data.get("result") or {}
            if not isinstance(dsl, dict):
                raise ValueError(f"LLM returned non-dict DSL: {dsl!r}")
            return dsl
        except requests.exceptions.ConnectionError:
            raise RuntimeError(f"LLM service unreachable at {LLM_SERVICE_URL}.")
        except requests.exceptions.HTTPError as exc:
            raise RuntimeError(f"LLM service error: {exc.response.text}") from exc

    def _generate_python_code(
        self,
        nl_query: str,
        column_names: list,
        model: Optional[str] = None,
        backend: str = "openrouter",
    ) -> str:
        endpoint = f"{LLM_SERVICE_URL}/code/generate"
        payload: Dict[str, Any] = {
            "user_message": nl_query,
            "available_columns": column_names,
            "backend": backend,
        }
        if model:
            payload["model"] = model

        try:
            resp = requests.post(endpoint, json=payload, timeout=90)
            resp.raise_for_status()
            data = resp.json()
            return data.get("code", "")
        except requests.exceptions.ConnectionError:
            raise RuntimeError(f"LLM service unreachable at {LLM_SERVICE_URL}.")
        except requests.exceptions.HTTPError as exc:
            raise RuntimeError(f"LLM service error: {exc.response.text}") from exc

    def _execute_and_persist(
        self,
        dataset: Dataset,
        dsl: AnalysisDSL,
        nl_query: Optional[str] = None,
        custom_label: Optional[str] = None,
    ) -> Dict[str, Any]:
        import pandas as pd

        df = self._dataset_service.load_dataframe(dataset)

        datetime_candidates = [
            col for col, meta in (dataset.columns_metadata or {}).items()
            if isinstance(meta, dict) and meta.get("type") in ("datetime", "datetime_string")
        ]
        for col in datetime_candidates:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        result_data = self._engine.execute(df, dsl)

        from analytics.domain.metrics.metrics_engine import MetricsEngine
        engine = MetricsEngine()
        result_data = engine._sanitize_value(result_data)

        analysis = Analysis.objects.create(
            dataset=dataset,
            metric_code="custom_dsl",
            chart_type=dsl.chart.type,
            config={},
            dsl_config=dsl.to_dict(),
            nl_query=nl_query or "",
            custom_label=custom_label or (nl_query[:100] if nl_query else "Custom Analysis"),
            is_custom=True,
            status="completed",
            completed_at=timezone.now(),
        )

        AnalysisResult.objects.create(
            analysis=analysis,
            chart_data=result_data.get("chart_data", {}),
            chart_image=result_data.get("chart_image", ""),
            statistics=result_data.get("statistics", {}),
        )

        return {
            "status": "completed",
            "analysis_id": str(analysis.id),
            "dataset_id": str(dataset.id),
            "mode": "custom_dsl",
            "dsl": dsl.to_dict(),
            "nl_query": nl_query,
            "chart_type": dsl.chart.type,
            "chart_data": result_data.get("chart_data", {}),
            "chart_image": result_data.get("chart_image", ""),
            "statistics": result_data.get("statistics", {}),
            "generated_at": analysis.completed_at.isoformat(),
        }

    @staticmethod
    def _safe_exec_python(code: str, df: object) -> Dict[str, Any]:
        """
        Execute user-provided Python code in a restricted environment.
        The code must set `result_data` (list of {label, value} dicts) and `chart_type`.
        """
        import pandas as pd
        import numpy as np

        allowed_builtins = {
            "print": print, "len": len, "range": range, "enumerate": enumerate,
            "zip": zip, "sorted": sorted, "list": list, "dict": dict, "set": set,
            "str": str, "int": int, "float": float, "round": round, "bool": bool,
            "sum": sum, "min": min, "max": max, "abs": abs, "all": all, "any": any,
            "isinstance": isinstance, "hasattr": hasattr, "getattr": getattr,
            "None": None, "True": True, "False": False,
            "map": map, "filter": filter, "reversed": reversed,
            "__import__": None,  # block imports
        }

        exec_globals: Dict[str, Any] = {
            "__builtins__": allowed_builtins,
            "pd": pd,
            "np": np,
            "df": df,
            "result_data": [],
            "chart_type": "bar",
            "statistics": {},
        }

        try:
            exec(code, exec_globals)  # noqa: S102
        except Exception as exc:
            return {"error": f"Python execution error: {exc}"}

        result_data = exec_globals.get("result_data", [])
        if not isinstance(result_data, list):
            result_data = []

        return {
            "result_data": result_data,
            "chart_type": exec_globals.get("chart_type", "bar"),
            "statistics": exec_globals.get("statistics", {}),
        }

    @staticmethod
    def _result_data_to_chart(result_data: list, chart_type: str, label: Optional[str] = None) -> Dict[str, Any]:
        """Convert [{label, value}] list to Chart.js-compatible chart_data."""
        labels = [str(item.get("label", "")) for item in result_data]
        values = [item.get("value") for item in result_data]

        return {
            "type": chart_type,
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": label or "Result",
                    "data": values,
                }],
            },
        }

    @staticmethod
    def _dsl_to_plan(dsl: AnalysisDSL) -> Dict[str, Any]:
        """Extract human-readable plan from a parsed DSL."""
        plan: Dict[str, Any] = {
            "chart_type": dsl.chart.type,
            "metric": dsl.select.metric or (dsl.select.metrics[0] if dsl.select.metrics else None),
            "aggregation": dsl.select.aggregation,
            "group_by": None,
            "filters": [],
            "limit": dsl.limit,
            "sort": None,
            "derived_column": None,
            "series": [],
        }

        if dsl.group_by.column:
            plan["group_by"] = {"type": "column", "column": dsl.group_by.column}
        elif dsl.group_by.time_column:
            plan["group_by"] = {
                "type": "time",
                "column": dsl.group_by.time_column,
                "period": dsl.group_by.time_period,
            }

        plan["filters"] = [
            {"column": f.column, "op": f.op, "value": f.value}
            for f in dsl.filters
        ]

        if dsl.sort.by:
            plan["sort"] = {"by": dsl.sort.by, "order": dsl.sort.order}

        if dsl.derived_column:
            plan["derived_column"] = {
                "name": dsl.derived_column.name,
                "formula": dsl.derived_column.formula,
            }

        if dsl.series:
            plan["series"] = [
                {"metric": s.metric, "aggregation": s.aggregation, "label": s.label}
                for s in dsl.series
            ]

        return plan
