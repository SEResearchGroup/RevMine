from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_ANALYSIS_LLM_MODEL = "openai/gpt-4o-mini"
MAX_PROMPT_LENGTH = 4000
MAX_LIST_ITEMS = 50
MAX_STRING_LENGTH = 200

VISUALIZATION_ALIASES = {
    "line_chart": "line",
    "line": "line",
    "time_series": "line",
    "timeseries": "line",
    "bar_chart": "bar",
    "bar": "bar",
    "column_chart": "bar",
    "pie_chart": "pie",
    "pie": "pie",
    "scatter_plot": "scatter",
    "scatter": "scatter",
    "histogram": "histogram",
    "area_chart": "area",
    "area": "area",
}

FILTER_COLUMN_CANDIDATES = {
    "date_range": [
        "Creation_Date",
        "created_at",
        "pr_creation_date",
        "mr_creation_date",
    ],
    "repositories": [
        "repository",
        "repository_name",
        "repo_name",
        "project",
        "project_name",
    ],
    "authors": [
        "author",
        "commit_author",
        "pr_author",
        "mr_author",
        "review_author",
        "Commiters",
    ],
}

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class AnalysisAutomationValidationError(ValueError):
    """Raised when the LLM analysis draft cannot be normalized safely."""


def sanitize_analysis_prompt(prompt: Any) -> str:
    """Trim user prompt, remove control characters, and cap payload size."""
    if not isinstance(prompt, str):
        raise AnalysisAutomationValidationError("prompt must be a string")

    sanitized = re.sub(r"[\x00-\x08\x0B-\x1F\x7F]", " ", prompt)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()

    if not sanitized:
        raise AnalysisAutomationValidationError("prompt is required")

    if len(sanitized) > MAX_PROMPT_LENGTH:
        raise AnalysisAutomationValidationError(
            f"prompt must be at most {MAX_PROMPT_LENGTH} characters"
        )

    return sanitized


def build_llm_analysis_prompt(
    dataset_id: str,
    dataset_columns: list[str],
    available_metrics: list[dict[str, Any]],
    user_prompt: str,
) -> str:
    """Inject dataset-aware constraints into the LLM request."""
    metric_lines = []
    for metric in available_metrics:
        metric_lines.append(
            "- {code}: {name} | supported_chart_types={chart_types} | required_columns={required_columns}".format(
                code=metric.get("code"),
                name=metric.get("name"),
                chart_types=", ".join(metric.get("supported_chart_types") or []),
                required_columns=", ".join(metric.get("required_columns") or []),
            )
        )

    columns_text = ", ".join(dataset_columns) if dataset_columns else "none"
    metrics_text = "\n".join(metric_lines) if metric_lines else "- none"

    return (
        "Dataset context for analysis request.\n"
        f"Dataset ID: {dataset_id}\n"
        f"Dataset columns: {columns_text}\n"
        "Only choose metrics from this available list for the response:\n"
        f"{metrics_text}\n\n"
        "If a requested filter cannot be mapped to the dataset context, keep it empty.\n"
        "User request:\n"
        f"{user_prompt}"
    )


def normalize_analysis_automation_payload(
    *,
    llm_payload: dict[str, Any],
    available_metrics: list[dict[str, Any]],
    dataset_columns: list[str],
) -> dict[str, Any]:
    """Validate and normalize LLM output into runnable analysis payloads."""
    if not isinstance(llm_payload, dict):
        raise AnalysisAutomationValidationError("LLM response must be a JSON object")

    result = llm_payload.get("result")
    if not isinstance(result, dict):
        raise AnalysisAutomationValidationError("LLM response result must be a JSON object")

    if result.get("intent") != "analyze":
        raise AnalysisAutomationValidationError("LLM response intent must be 'analyze'")

    warnings: list[str] = []
    metrics_by_code = {
        metric.get("code"): metric
        for metric in available_metrics
        if isinstance(metric, dict) and metric.get("code")
    }
    normalized_metrics = _normalize_metric_codes(
        result.get("metrics"),
        metrics_by_code,
        warnings,
    )
    if not normalized_metrics:
        raise AnalysisAutomationValidationError(
            "LLM response did not include any valid available analysis metrics"
        )

    dimensions = _normalize_string_list(result.get("dimensions"))
    original_visualization = result.get("visualization")
    normalized_chart_type = _normalize_visualization(
        original_visualization,
        warnings,
    )
    original_filters, applied_filters = _normalize_filters(
        result.get("filters"),
        dataset_columns,
        warnings,
    )

    analyses = []
    for metric_code in normalized_metrics:
        metric = metrics_by_code[metric_code]
        chart_type = _resolve_chart_type(metric, normalized_chart_type, warnings)
        config = {
            "filters": applied_filters,
            "custom_params": {
                "dimensions": dimensions,
                "selection_mode": "ai_prompt",
            },
        }
        if metric.get("supports_time_aggregation"):
            config["time_aggregation"] = "M"

        analyses.append(
            {
                "metric_code": metric_code,
                "chart_type": chart_type,
                "config": config,
            }
        )

    logger.info(
        "Normalized analysis automation draft metrics=%s visualization=%s warnings=%s",
        normalized_metrics,
        normalized_chart_type,
        warnings,
    )

    return {
        "model": llm_payload.get("model") or DEFAULT_ANALYSIS_LLM_MODEL,
        "selection": {
            "metrics": normalized_metrics,
            "dimensions": dimensions,
            "filters": original_filters,
            "applied_filters": applied_filters,
            "visualization": original_visualization,
            "chart_type": normalized_chart_type,
        },
        "analyses": analyses,
        "warnings": warnings,
    }


def _normalize_metric_codes(
    raw_metrics: Any,
    metrics_by_code: dict[str, dict[str, Any]],
    warnings: list[str],
) -> list[str]:
    values = _normalize_string_list(raw_metrics)
    normalized: list[str] = []

    for value in values:
        if value not in metrics_by_code:
            warnings.append(f"Ignored unavailable metric '{value}'.")
            continue
        if value not in normalized:
            normalized.append(value)

    return normalized


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    normalized: list[str] = []
    for item in value[:MAX_LIST_ITEMS]:
        if not isinstance(item, str):
            continue
        cleaned = re.sub(r"\s+", " ", item).strip()
        if not cleaned:
            continue
        if len(cleaned) > MAX_STRING_LENGTH:
            cleaned = cleaned[:MAX_STRING_LENGTH].strip()
        if cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


def _normalize_visualization(value: Any, warnings: list[str]) -> str | None:
    if not isinstance(value, str):
        return None

    cleaned = value.strip().lower()
    if not cleaned:
        return None

    chart_type = VISUALIZATION_ALIASES.get(cleaned)
    if chart_type is None:
        warnings.append(f"Visualization '{value}' is not supported, using metric defaults.")
    return chart_type


def _normalize_filters(
    raw_filters: Any,
    dataset_columns: list[str],
    warnings: list[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    default_filters = {
        "date_range": None,
        "repositories": [],
        "authors": [],
    }
    if not isinstance(raw_filters, dict):
        return default_filters, {}

    normalized_filters = {
        "date_range": _normalize_date_range(raw_filters.get("date_range"), warnings),
        "repositories": _normalize_string_list(raw_filters.get("repositories")),
        "authors": _normalize_string_list(raw_filters.get("authors")),
    }

    applied_filters: dict[str, Any] = {}

    date_column = _find_first_matching_column(dataset_columns, FILTER_COLUMN_CANDIDATES["date_range"])
    if normalized_filters["date_range"]:
        if date_column:
            applied_filters[date_column] = {
                key: value
                for key, value in (
                    ("min", normalized_filters["date_range"].get("start_date")),
                    ("max", normalized_filters["date_range"].get("end_date")),
                )
                if value
            }
        else:
            warnings.append("Date filter could not be applied because the dataset has no supported date column.")

    repository_column = _find_first_matching_column(dataset_columns, FILTER_COLUMN_CANDIDATES["repositories"])
    if normalized_filters["repositories"]:
        if repository_column:
            applied_filters[repository_column] = normalized_filters["repositories"]
        else:
            warnings.append("Repository filter could not be applied because the dataset has no supported repository column.")

    author_column = _find_first_matching_column(dataset_columns, FILTER_COLUMN_CANDIDATES["authors"])
    if normalized_filters["authors"]:
        if author_column:
            applied_filters[author_column] = normalized_filters["authors"]
        else:
            warnings.append("Author filter could not be applied because the dataset has no supported author column.")

    return normalized_filters, applied_filters


def _normalize_date_range(value: Any, warnings: list[str]) -> dict[str, str] | None:
    if value in (None, ""):
        return None
    if not isinstance(value, dict):
        warnings.append("Ignored invalid date_range filter from LLM response.")
        return None

    start_date = value.get("start_date")
    end_date = value.get("end_date")

    if start_date is not None and not _is_valid_date_string(start_date):
        warnings.append("Ignored invalid start_date in LLM response.")
        start_date = None
    if end_date is not None and not _is_valid_date_string(end_date):
        warnings.append("Ignored invalid end_date in LLM response.")
        end_date = None

    if not start_date and not end_date:
        return None

    return {
        "start_date": start_date,
        "end_date": end_date,
    }


def _is_valid_date_string(value: Any) -> bool:
    return isinstance(value, str) and bool(DATE_PATTERN.fullmatch(value.strip()))


def _find_first_matching_column(dataset_columns: list[str], candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in dataset_columns:
            return candidate
    return None


def _resolve_chart_type(
    metric: dict[str, Any],
    requested_chart_type: str | None,
    warnings: list[str],
) -> str:
    supported = metric.get("supported_chart_types") or []
    default = metric.get("default_chart_type") or (supported[0] if supported else "bar")

    if requested_chart_type and requested_chart_type in supported:
        return requested_chart_type

    if requested_chart_type and requested_chart_type not in supported:
        warnings.append(
            f"Visualization '{requested_chart_type}' is not supported for metric '{metric.get('code')}', using '{default}'."
        )

    return default
