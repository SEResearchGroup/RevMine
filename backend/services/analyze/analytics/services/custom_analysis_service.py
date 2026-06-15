from __future__ import annotations

import os
from typing import Any

import requests

from analytics.domain.analysis.custom_formula import (
    ALLOWED_AGGREGATIONS,
    ALLOWED_CHART_TYPES,
    ALLOWED_SCOPES,
    referenced_columns,
    slugify_output_column,
)


class CustomAnalysisValidationError(ValueError):
    """Raised when a custom-analysis preview request is invalid."""


class CustomAnalysisServiceError(RuntimeError):
    """Raised when the LLM service cannot provide a usable suggestion."""


def _metadata_type(meta: Any) -> str:
    if isinstance(meta, dict):
        return meta.get("type") or meta.get("dtype") or "unknown"
    return str(meta or "unknown")


class CustomAnalysisSuggestionService:
    """Generate and normalize LLM suggestions for custom formula analyses."""

    @classmethod
    def generate_preview(cls, dataset, payload: dict[str, Any]) -> dict[str, Any]:
        prompt = str(payload.get("prompt") or "").strip()
        if not prompt:
            raise CustomAnalysisValidationError("prompt is required")

        parsed = cls._call_llm(
            provider=payload.get("llm_provider") or "openrouter",
            model=payload.get("model"),
            user_message=cls._build_user_message(dataset, prompt),
        )
        suggestion, warnings = cls._normalize_suggestion(dataset, parsed)
        return {
            "success": True,
            "prompt": prompt,
            "suggestion": suggestion,
            "warnings": warnings,
            "raw": parsed,
        }

    @staticmethod
    def _call_llm(provider: str, model: str | None, user_message: str) -> dict[str, Any]:
        selected_provider = provider if provider in {"openrouter", "ollama"} else "openrouter"
        base_url = os.getenv(
            "LLM_SERVICE_URL",
            "http://llm-service:8004/api/v1/llm",
        ).rstrip("/")
        timeout = float(os.getenv("LLM_SERVICE_TIMEOUT", "75"))

        try:
            response = requests.post(
                f"{base_url}/custom-analysis",
                json={"user_message": user_message, "model": model, "provider": selected_provider},
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise CustomAnalysisServiceError(f"LLM service unavailable: {exc}") from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise CustomAnalysisServiceError("LLM service returned a non-JSON response") from exc

        if response.status_code >= 400:
            detail = body.get("detail") or body.get("error") or body
            raise CustomAnalysisServiceError(f"LLM service error: {detail}")

        result = body.get("result")
        if not isinstance(result, dict):
            raise CustomAnalysisServiceError("LLM service response is missing a result object")

        return result

    @staticmethod
    def _build_user_message(dataset, prompt: str) -> str:
        columns = [
            {
                "name": name,
                "type": _metadata_type(meta),
                "nullable": bool(isinstance(meta, dict) and meta.get("null_count", 0) > 0),
            }
            for name, meta in (dataset.columns_metadata or {}).items()
        ]
        return (
            "Create one custom RevMine analysis formula for this dataset.\n"
            f"Dataset filename: {dataset.filename}\n"
            f"Columns: {columns}\n"
            f"Allowed aggregation_scope values: {sorted(ALLOWED_SCOPES)}\n"
            f"Allowed aggregations: {sorted(ALLOWED_AGGREGATIONS)}\n"
            f"Allowed chart types: {sorted(ALLOWED_CHART_TYPES)}\n"
            "Use formula references in [Column Name] format exactly as listed.\n"
            "User request:\n"
            f"{prompt}"
        )

    @classmethod
    def _normalize_suggestion(
        cls, dataset, parsed: dict[str, Any]
    ) -> tuple[dict[str, Any], list[str]]:
        data = parsed.get("custom_analysis") if isinstance(parsed.get("custom_analysis"), dict) else parsed
        columns = set((dataset.columns_metadata or {}).keys())
        warnings: list[str] = []

        formula = str(data.get("formula") or "").strip()
        if not formula:
            raise CustomAnalysisServiceError("The LLM response did not include a formula")

        refs = referenced_columns(formula)
        for column in refs:
            if column not in columns:
                raise CustomAnalysisServiceError(
                    f"The LLM referenced column '{column}', which is not in the dataset"
                )

        name = str(data.get("name") or data.get("title") or "Custom analysis").strip()
        output_column = slugify_output_column(data.get("output_column") or name)

        scope = str(data.get("aggregation_scope") or data.get("scope") or "mr").strip()
        if scope not in ALLOWED_SCOPES:
            warnings.append(f"Unsupported aggregation scope '{scope}' was replaced with 'mr'.")
            scope = "mr"

        aggregation = str(data.get("aggregation") or "sum").strip()
        if aggregation not in ALLOWED_AGGREGATIONS:
            warnings.append(f"Unsupported aggregation '{aggregation}' was replaced with 'sum'.")
            aggregation = "sum"

        chart_type = str(data.get("chart_type") or ("line" if scope == "time" else "bar")).strip()
        if chart_type not in ALLOWED_CHART_TYPES:
            warnings.append(f"Unsupported chart type '{chart_type}' was replaced with 'bar'.")
            chart_type = "bar"

        x_axis = data.get("x_axis") or data.get("date_column")
        if x_axis and x_axis not in columns:
            warnings.append(f"Suggested X axis '{x_axis}' is not available and was removed.")
            x_axis = None

        if scope == "time" and not x_axis:
            x_axis = cls._first_column_of_type(dataset, {"datetime", "datetime_string"})
            if not x_axis:
                warnings.append("No datetime column was found; the analysis was changed to per-MR.")
                scope = "mr"

        if scope == "category" and not x_axis:
            x_axis = cls._first_column_of_type(dataset, {"categorical", "numeric_categorical"})
            if not x_axis:
                warnings.append("No categorical column was found; the analysis was changed to per-MR.")
                scope = "mr"

        config = {
            "name": name,
            "formula": formula,
            "output_column": output_column,
            "aggregation_scope": scope,
            "aggregation": aggregation,
            "chart_type": chart_type,
            "time_aggregation": data.get("time_aggregation") or "M",
            "persist_column": True,
        }
        if x_axis:
            config["x_axis"] = x_axis

        return {
            "name": name,
            "formula": formula,
            "metric_code": "custom_formula",
            "chart_type": chart_type,
            "config": config,
        }, warnings

    @staticmethod
    def _first_column_of_type(dataset, expected_types: set[str]) -> str | None:
        for name, meta in (dataset.columns_metadata or {}).items():
            if _metadata_type(meta) in expected_types:
                return name
        return None
