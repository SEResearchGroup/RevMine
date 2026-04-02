import pytest

from users.services.collection_automation import (
    CollectionAutomationValidationError,
    normalize_collection_automation_payload,
    sanitize_user_prompt,
)


def test_sanitize_user_prompt_trims_and_rejects_empty():
    assert sanitize_user_prompt("  collect bug fixes \n\n ") == "collect bug fixes"

    with pytest.raises(CollectionAutomationValidationError, match="prompt is required"):
        sanitize_user_prompt(" \n\t ")


def test_normalize_collection_automation_payload_maps_aliases_and_adds_dependencies():
    llm_payload = {
        "model": "openai/gpt-4o-mini",
        "result": {
            "intent": "collect",
            "platform": "gitlab",
            "branch": ["release/2025", "main"],
            "metrics": ["creation_date", "commit_messages", "bad_metric"],
            "basic_filters": {
                "date_range": {
                    "start_date": "2025-10-01",
                    "end_date": "2026-04-01",
                },
                "pr_status": ["opened", "merged"],
            },
            "cleaning_filters": {
                "refined_date_range": {
                    "start_date": "2025-11-01",
                    "end_date": "2026-03-01",
                },
                "file_extensions": ["py", ".JS"],
                "authors": ["alice", "alice", "bob"],
                "keywords": {
                    "fields": ["title", "bad_field"],
                    "terms": ["bug", "fix"],
                },
            },
            "features": ["lead_time", "comments_count", "unknown_feature"],
        },
    }
    repository_details = {
        "name": "demo",
        "full_name": "acme/demo",
        "platform": "github",
        "default_branch": "main",
    }
    branches = [{"name": "main"}, {"name": "develop"}]

    normalized = normalize_collection_automation_payload(
        llm_payload=llm_payload,
        repository_details=repository_details,
        available_branches=branches,
    )

    assert normalized["draft"]["collection"]["platform"] == "github"
    assert normalized["draft"]["collection"]["branch_name"] == "main"
    assert normalized["draft"]["collection"]["status"] == ["open", "merged"]
    assert normalized["draft"]["collection"]["selected_metrics"] == [
        "pr_creation_date",
        "commit_message",
        "pr_merge_date",
        "pr_state",
        "pr_comments",
        "review_body",
        "review_comment_body",
    ]
    assert normalized["draft"]["cleaning"]["selected_features"] == [
        "Lead_Time",
        "comments",
    ]
    assert normalized["draft"]["cleaning"]["filters"]["file_extensions"] == [
        ".py",
        ".js",
    ]
    assert normalized["draft"]["cleaning"]["filters"]["authors"] == ["alice", "bob"]
    assert normalized["draft"]["cleaning"]["filters"]["keyword_filters"] == [
        {"field": "title", "keywords": ["bug", "fix"]}
    ]
    assert normalized["warnings"]


def test_normalize_collection_automation_payload_requires_valid_metrics():
    llm_payload = {
        "model": "openai/gpt-4o-mini",
        "result": {
            "intent": "collect",
            "platform": "github",
            "branch": [],
            "metrics": ["unknown_metric"],
            "basic_filters": {},
            "cleaning_filters": {},
            "features": [],
        },
    }
    repository_details = {
        "name": "demo",
        "full_name": "acme/demo",
        "platform": "github",
        "default_branch": "main",
    }

    with pytest.raises(
        CollectionAutomationValidationError,
        match="did not include any valid collection metrics",
    ):
        normalize_collection_automation_payload(
            llm_payload=llm_payload,
            repository_details=repository_details,
            available_branches=[{"name": "main"}],
        )


def test_normalize_collection_automation_payload_defaults_to_all_metrics_when_empty():
    llm_payload = {
        "model": "openai/gpt-4o-mini",
        "result": {
            "intent": "collect",
            "platform": "gitlab",
            "branch": [],
            "metrics": [],
            "basic_filters": {
                "date_range": {
                    "start_date": "2025-10-01",
                    "end_date": "2026-04-01",
                }
            },
            "cleaning_filters": {},
            "features": [],
        },
    }
    repository_details = {
        "name": "demo",
        "full_name": "acme/demo",
        "platform": "gitlab",
        "default_branch": "main",
    }

    normalized = normalize_collection_automation_payload(
        llm_payload=llm_payload,
        repository_details=repository_details,
        available_branches=[{"name": "main"}],
    )

    assert normalized["draft"]["collection"]["selected_metrics"]
    assert "mr_title" in normalized["draft"]["collection"]["selected_metrics"]
    assert "change_deleted_file" in normalized["draft"]["collection"]["selected_metrics"]
    assert any(
        "all available metrics were selected by default" in warning
        for warning in normalized["warnings"]
    )
