"""AnalysisPlanner — asks the LLM to turn a natural-language request into an AnalysisPlan."""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import requests

from analytics.domain.analysis.custom_formula import (
    ALLOWED_AGGREGATIONS,
    ALLOWED_CHART_TYPES,
    ALLOWED_SCOPES,
    referenced_columns,
    slugify_output_column,
)
from analytics.pipeline.base import (
    SCENARIO_CSV_DERIVED,
    SCENARIO_CSV_EXISTING,
    SCENARIO_RAW_JSON,
    AnalysisPlan,
    AnalysisRequest,
)

logger = logging.getLogger(__name__)

_VALID_SCENARIOS = {SCENARIO_CSV_EXISTING, SCENARIO_CSV_DERIVED, SCENARIO_RAW_JSON}

# Matches LLM mistakes like mean([Lead_Time]) or sum([#Commits])
_AGG_WRAPPER_RE = re.compile(
    r"^(?:mean|sum|count|median|min|max|std)\s*\(\s*(\[[^\]]+\]|[A-Za-z_]\w*)\s*\)\s*$",
    re.IGNORECASE,
)


def _sanitize_formula(formula: str | None, scenario: str, warnings: list[str]) -> str | None:
    """Strip aggregation wrappers that the LLM sometimes puts in the formula field."""
    if not formula:
        return formula

    m = _AGG_WRAPPER_RE.match(formula.strip())
    if m:
        inner = m.group(1)
        if not inner.startswith("["):
            inner = f"[{inner}]"
        warnings.append(
            f"Formula '{formula}' uses an aggregation function which belongs in the "
            "'aggregation' field, not the formula. Simplified to column reference."
        )
        formula = inner

    # For csv_existing with a plain single-column reference, drop the formula —
    # the output_column field already identifies which column to aggregate.
    if scenario == SCENARIO_CSV_EXISTING:
        refs = referenced_columns(formula)
        bare = formula.strip()
        if len(refs) == 1 and bare in (f"[{refs[0]}]", refs[0]):
            return None

    return formula


class AnalysisPlannerError(RuntimeError):
    """Raised when the LLM cannot produce a usable plan."""


def _metadata_type(meta: Any) -> str:
    if isinstance(meta, dict):
        return meta.get("type") or meta.get("dtype") or "unknown"
    return str(meta or "unknown")


def _build_user_message(request: AnalysisRequest) -> str:
    columns = [
        {
            "name": name,
            "type": _metadata_type(meta),
            "nullable": bool(isinstance(meta, dict) and meta.get("null_count", 0) > 0),
        }
        for name, meta in request.columns_metadata.items()
    ]
    return (
        "Dataset columns:\n"
        f"{json.dumps(columns, indent=2)}\n\n"
        f"Allowed aggregation_scope values: {sorted(ALLOWED_SCOPES)}\n"
        f"Allowed aggregations: {sorted(ALLOWED_AGGREGATIONS)}\n"
        f"Allowed chart types: {sorted(ALLOWED_CHART_TYPES)}\n\n"
        f"User request:\n{request.prompt}"
    )


def _call_llm(request: AnalysisRequest) -> dict[str, Any]:
    base_url = os.getenv(
        "LLM_SERVICE_URL", "http://llm-service:8004/api/v1/llm"
    ).rstrip("/")
    timeout = float(os.getenv("LLM_SERVICE_TIMEOUT", "75"))

    payload = {
        "user_message": _build_user_message(request),
        "model": request.model,
        "provider": request.llm_provider,
    }

    try:
        resp = requests.post(
            f"{base_url}/analysis-plan",
            json=payload,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise AnalysisPlannerError(f"LLM service unavailable: {exc}") from exc

    try:
        body = resp.json()
    except ValueError as exc:
        raise AnalysisPlannerError("LLM service returned a non-JSON response") from exc

    if resp.status_code >= 400:
        detail = body.get("detail") or body.get("error") or body
        raise AnalysisPlannerError(f"LLM service error ({resp.status_code}): {detail}")

    result = body.get("result")
    if not isinstance(result, dict):
        raise AnalysisPlannerError("LLM service response is missing the 'result' object")

    return result


def _parse_plan(raw: dict[str, Any], columns_metadata: dict) -> AnalysisPlan:
    available_columns = set(columns_metadata.keys())
    warnings: list[str] = []

    scenario = str(raw.get("scenario") or SCENARIO_CSV_DERIVED).strip()
    if scenario not in _VALID_SCENARIOS:
        warnings.append(f"Unknown scenario '{scenario}'; falling back to 'csv_derived'.")
        scenario = SCENARIO_CSV_DERIVED

    name = str(raw.get("name") or "Custom analysis").strip()
    explanation = str(raw.get("explanation") or "").strip()
    formula = raw.get("formula") or None
    if formula is not None:
        formula = str(formula).strip() or None

    # Strip aggregation wrappers (mean([col]), sum([col]), ...) the LLM sometimes generates.
    # For csv_existing with a plain column reference, formula is reduced to None.
    formula = _sanitize_formula(formula, scenario, warnings)

    # If the LLM wrapped an aggregation around a column, prefer that column as output_column.
    raw_output = raw.get("output_column") or name
    if not raw.get("output_column") and formula is None and scenario == SCENARIO_CSV_EXISTING:
        # Try to extract a clean column name from metrics_needed or x_axis fallback
        metrics_ref = raw.get("metrics_needed") or []
        if metrics_ref and isinstance(metrics_ref[0], str):
            raw_output = metrics_ref[0]

    output_column = slugify_output_column(raw_output)

    metrics_needed = [
        m for m in (raw.get("metrics_needed") or []) if isinstance(m, str)
    ]

    scope = str(raw.get("aggregation_scope") or "mr").strip()
    if scope not in ALLOWED_SCOPES:
        warnings.append(f"Unsupported scope '{scope}'; falling back to 'mr'.")
        scope = "mr"

    aggregation = str(raw.get("aggregation") or "mean").strip()
    if aggregation not in ALLOWED_AGGREGATIONS:
        warnings.append(f"Unsupported aggregation '{aggregation}'; falling back to 'mean'.")
        aggregation = "mean"

    chart_type = str(raw.get("chart_type") or ("line" if scope == "time" else "bar")).strip()
    if chart_type not in ALLOWED_CHART_TYPES:
        warnings.append(f"Unsupported chart type '{chart_type}'; falling back to 'bar'.")
        chart_type = "bar"

    x_axis = raw.get("x_axis") or None
    if x_axis and x_axis not in available_columns:
        warnings.append(f"Suggested x_axis '{x_axis}' is not in the dataset; removing it.")
        x_axis = None

    time_aggregation = str(raw.get("time_aggregation") or "M").strip()

    if warnings:
        logger.warning(
            "AnalysisPlanner normalisation warnings",
            extra={"warnings": warnings, "event": "analysis_plan_normalized"},
        )

    return AnalysisPlan(
        scenario=scenario,
        name=name,
        explanation=explanation,
        formula=formula,
        output_column=output_column,
        metrics_needed=metrics_needed,
        aggregation_scope=scope,
        aggregation=aggregation,
        chart_type=chart_type,
        x_axis=x_axis,
        time_aggregation=time_aggregation,
    )


class AnalysisPlanner:
    """Calls the LLM to convert a natural-language prompt into an AnalysisPlan."""

    @staticmethod
    def plan(request: AnalysisRequest) -> AnalysisPlan:
        raw = _call_llm(request)
        return _parse_plan(raw, request.columns_metadata)
