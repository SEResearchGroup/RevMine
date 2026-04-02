import pytest

from users.services.analysis_automation import (
    AnalysisAutomationValidationError,
    normalize_analysis_automation_payload,
    sanitize_analysis_prompt,
)


AVAILABLE_METRICS = [
    {
        "code": "commits_over_time",
        "name": "Commits Over Time",
        "default_chart_type": "line",
        "supported_chart_types": ["line", "bar", "area"],
        "required_columns": ["Creation_Date", "#Commits"],
        "supports_time_aggregation": True,
    },
    {
        "code": "state_distribution",
        "name": "State Distribution",
        "default_chart_type": "pie",
        "supported_chart_types": ["pie", "bar"],
        "required_columns": ["state"],
        "supports_time_aggregation": False,
    },
]


def test_sanitize_analysis_prompt_trims_and_rejects_empty():
    assert sanitize_analysis_prompt("  show me commits over time \n") == "show me commits over time"

    with pytest.raises(AnalysisAutomationValidationError, match="prompt is required"):
        sanitize_analysis_prompt(" \n\t ")


def test_normalize_analysis_payload_maps_metrics_filters_and_chart_type():
    llm_payload = {
        "model": "openai/gpt-4o-mini",
        "result": {
            "intent": "analyze",
            "metrics": ["commits_over_time", "unknown_metric"],
            "dimensions": ["repository_name"],
            "filters": {
                "date_range": {
                    "start_date": "2025-01-01",
                    "end_date": "2025-12-31",
                },
                "repositories": ["acme/api"],
                "authors": ["alice"],
            },
            "visualization": "line_chart",
        },
    }

    normalized = normalize_analysis_automation_payload(
        llm_payload=llm_payload,
        available_metrics=AVAILABLE_METRICS,
        dataset_columns=["Creation_Date", "repository_name", "commit_author"],
    )

    assert normalized["selection"]["metrics"] == ["commits_over_time"]
    assert normalized["selection"]["chart_type"] == "line"
    assert normalized["selection"]["applied_filters"] == {
        "Creation_Date": {
            "min": "2025-01-01",
            "max": "2025-12-31",
        },
        "repository_name": ["acme/api"],
        "commit_author": ["alice"],
    }
    assert normalized["analyses"] == [
        {
            "metric_code": "commits_over_time",
            "chart_type": "line",
            "config": {
                "filters": {
                    "Creation_Date": {
                        "min": "2025-01-01",
                        "max": "2025-12-31",
                    },
                    "repository_name": ["acme/api"],
                    "commit_author": ["alice"],
                },
                "custom_params": {
                    "dimensions": ["repository_name"],
                    "selection_mode": "ai_prompt",
                },
                "time_aggregation": "M",
            },
        }
    ]
    assert normalized["warnings"]


def test_normalize_analysis_payload_requires_valid_available_metrics():
    llm_payload = {
        "model": "openai/gpt-4o-mini",
        "result": {
            "intent": "analyze",
            "metrics": ["unknown_metric"],
            "dimensions": [],
            "filters": {},
            "visualization": "bar_chart",
        },
    }

    with pytest.raises(
        AnalysisAutomationValidationError,
        match="did not include any valid available analysis metrics",
    ):
        normalize_analysis_automation_payload(
            llm_payload=llm_payload,
            available_metrics=AVAILABLE_METRICS,
            dataset_columns=["Creation_Date"],
        )
