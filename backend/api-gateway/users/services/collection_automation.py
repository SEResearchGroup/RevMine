from __future__ import annotations

import logging
import re
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_LLM_MODEL = "openai/gpt-4o-mini"
DEFAULT_COLLECTION_STATUSES = ["open", "closed", "merged"]
VALID_KEYWORD_FIELDS = {
    "title": "title",
    "description": "description",
    "comments": "comments",
    "commit_message": "commit_message",
}
MAX_PROMPT_LENGTH = 4000
MAX_LIST_ITEMS = 50
MAX_STRING_LENGTH = 200


class CollectionAutomationValidationError(ValueError):
    """Raised when the LLM draft cannot be normalized safely."""


FEATURE_ALIASES = {
    "creation_date": "Creation_Date",
    "lead_time": "Lead_Time",
    "discussions_count": "#Discussions",
    "discussions": "#Discussions",
    "commits_count": "#Commits",
    "mean_time_between_commits": "Mean_Time_between_commits",
    "commiters": "Commiters",
    "commiters_list": "Commiters",
    "committers": "Commiters",
    "committers_list": "Commiters",
    "unique_commiters": "#UniqueCommiters",
    "unique_committers": "#UniqueCommiters",
    "minor_author": "nb_minor_author",
    "minor_authors": "nb_minor_author",
    "nb_minor_author": "nb_minor_author",
    "major_author": "nb_major_author",
    "major_authors": "nb_major_author",
    "nb_major_author": "nb_major_author",
    "delta_time": "delta_time",
    "churn_addition": "churn_addition",
    "churn_additions": "churn_addition",
    "churn_deletions": "churn_deletions",
    "initial_size": "initial_size",
    "hist_entropy": "hist_entropy",
    "historical_entropy": "hist_entropy",
    "modified_files": "modified_files",
    "file_types": "filetypes",
    "filetypes": "filetypes",
    "state": "state",
    "rework_size": "rework_size",
    "people_count": "#people",
    "reviewers_count": "#reviewers",
    "commiters_count": "#commiters",
    "committers_count": "#commiters",
    "discussionners_count": "#discussionners",
    "discussers_count": "#discussionners",
    "total_additions": "additions",
    "additions": "additions",
    "total_deletions": "deletions",
    "deletions": "deletions",
    "comments_count": "comments",
    "comments": "comments",
}


PLATFORM_METRIC_ALIASES = {
    "github": {
        "pr_title": "pr_title",
        "pr_title_label": "pr_title",
        "pull_request_title": "pr_title",
        "pr_description": "pr_description",
        "pull_request_description": "pr_description",
        "pr_number": "pr_number",
        "pull_request_number": "pr_number",
        "pr_status": "pr_status",
        "pull_request_status": "pr_status",
        "pr_state": "pr_state",
        "pr_state_open_closed_merged": "pr_state",
        "pull_request_state": "pr_state",
        "pr_author": "pr_author",
        "pull_request_author": "pr_author",
        "creation_date": "pr_creation_date",
        "pr_creation_date": "pr_creation_date",
        "created_at": "pr_creation_date",
        "merge_date": "pr_merge_date",
        "pr_merge_date": "pr_merge_date",
        "merged_at": "pr_merge_date",
        "close_date": "pr_close_date",
        "pr_close_date": "pr_close_date",
        "closed_at": "pr_close_date",
        "merged_by": "pr_merged_by",
        "pr_merged_by": "pr_merged_by",
        "commit_sha": "commit_sha",
        "commit_messages": "commit_message",
        "commit_message": "commit_message",
        "commit_authors": "commit_author",
        "commit_author": "commit_author",
        "commit_dates": "commit_date",
        "commit_date": "commit_date",
        "file_changes": "commit_changes",
        "commit_changes": "commit_changes",
        "pr_comments": "pr_comments",
        "pr_discussion_comments": "pr_comments",
        "pull_request_comments": "pr_comments",
        "comment_authors": "pr_comment_author",
        "pr_comment_author": "pr_comment_author",
        "comment_dates": "pr_comment_date",
        "pr_comment_date": "pr_comment_date",
        "comment_content": "pr_comment_body",
        "pr_comment_body": "pr_comment_body",
        "review_state": "review_state",
        "review_state_approved_changes_requested_commented": "review_state",
        "reviewer": "review_author",
        "review_author": "review_author",
        "review_date": "review_date",
        "review_comments": "review_body",
        "review_body": "review_body",
        "inline_comments": "review_comment_body",
        "review_comment_body": "review_comment_body",
        "comment_author": "review_comment_author",
        "review_comment_author": "review_comment_author",
        "comment_date": "review_comment_date",
        "review_comment_date": "review_comment_date",
        "code_position": "review_comment_position",
        "review_comment_position": "review_comment_position",
        "file_path": "review_comment_path",
        "review_comment_path": "review_comment_path",
        "file_names": "file_name",
        "file_name": "file_name",
        "changed_files": "file_name",
        "file_status": "file_status",
        "file_status_added_modified_deleted": "file_status",
        "lines_added": "file_additions",
        "file_additions": "file_additions",
        "lines_deleted": "file_deletions",
        "file_deletions": "file_deletions",
        "total_changes": "file_changes",
    },
    "gitlab": {
        "mr_title": "mr_title",
        "merge_request_title": "mr_title",
        "mr_description": "mr_description",
        "merge_request_description": "mr_description",
        "mr_iid": "mr_iid",
        "mr_status": "mr_status",
        "merge_request_status": "mr_status",
        "mr_state": "mr_state",
        "merge_request_state": "mr_state",
        "mr_author": "mr_author",
        "merge_request_author": "mr_author",
        "creation_date": "mr_creation_date",
        "mr_creation_date": "mr_creation_date",
        "created_at": "mr_creation_date",
        "merge_date": "mr_merge_date",
        "mr_merge_date": "mr_merge_date",
        "merged_at": "mr_merge_date",
        "close_date": "mr_close_date",
        "mr_close_date": "mr_close_date",
        "closed_at": "mr_close_date",
        "merged_by": "mr_merged_by",
        "mr_merged_by": "mr_merged_by",
        "commit_id": "commit_id",
        "commit_messages": "commit_message",
        "commit_message": "commit_message",
        "commit_authors": "commit_author",
        "commit_author": "commit_author",
        "commit_dates": "commit_date",
        "commit_date": "commit_date",
        "file_changes_diff": "commit_changes",
        "commit_changes": "commit_changes",
        "discussion_id": "discussion_id",
        "discussion_notes": "discussion_notes",
        "discussion_comments": "discussion_notes",
        "resolved_status": "discussion_resolved",
        "discussion_resolved": "discussion_resolved",
        "note_content": "note_body",
        "note_body": "note_body",
        "note_author": "note_author",
        "note_date": "note_date",
        "note_type": "note_type",
        "old_file_path": "change_old_path",
        "change_old_path": "change_old_path",
        "new_file_path": "change_new_path",
        "change_new_path": "change_new_path",
        "file_diff": "change_diff",
        "change_diff": "change_diff",
        "new_file": "change_new_file",
        "change_new_file": "change_new_file",
        "renamed_file": "change_renamed_file",
        "change_renamed_file": "change_renamed_file",
        "deleted_file": "change_deleted_file",
        "change_deleted_file": "change_deleted_file",
    },
}


FEATURE_DEPENDENCIES = {
    "github": {
        "Creation_Date": ["pr_creation_date"],
        "Lead_Time": ["pr_creation_date", "pr_merge_date", "pr_state"],
        "#Discussions": ["pr_comments"],
        "#Commits": ["commit_sha"],
        "Mean_Time_between_commits": ["commit_date"],
        "Commiters": ["commit_author"],
        "#UniqueCommiters": ["commit_author"],
        "nb_minor_author": ["commit_author"],
        "nb_major_author": ["commit_author"],
        "delta_time": ["pr_creation_date"],
        "churn_addition": ["file_additions"],
        "churn_deletions": ["file_deletions"],
        "initial_size": ["file_additions", "file_deletions"],
        "hist_entropy": ["file_name", "file_changes"],
        "modified_files": ["file_name"],
        "filetypes": ["file_name"],
        "state": ["pr_state"],
        "rework_size": ["pr_comments", "file_additions", "file_deletions"],
        "#people": ["pr_author", "review_author", "commit_author", "pr_comment_author"],
        "#reviewers": ["review_author"],
        "#commiters": ["commit_author"],
        "#discussionners": ["pr_comment_author", "review_comment_author"],
        "additions": ["file_additions"],
        "deletions": ["file_deletions"],
        "comments": ["pr_comments", "review_body", "review_comment_body"],
    },
    "gitlab": {
        "Creation_Date": ["mr_creation_date"],
        "Lead_Time": ["mr_creation_date", "mr_merge_date", "mr_state"],
        "#Discussions": ["discussion_notes", "note_body"],
        "#Commits": ["commit_id"],
        "Mean_Time_between_commits": ["commit_date"],
        "Commiters": ["commit_author"],
        "#UniqueCommiters": ["commit_author"],
        "nb_minor_author": ["commit_author"],
        "nb_major_author": ["commit_author"],
        "delta_time": ["mr_creation_date"],
        "churn_addition": ["commit_changes"],
        "churn_deletions": ["commit_changes"],
        "initial_size": ["change_diff"],
        "hist_entropy": ["change_new_path"],
        "modified_files": ["change_new_path"],
        "filetypes": ["change_new_path"],
        "state": ["mr_state"],
        "rework_size": ["discussion_notes", "note_body", "change_diff"],
        "#people": ["mr_author", "note_author", "commit_author"],
        "#reviewers": ["note_author"],
        "#commiters": ["commit_author"],
        "#discussionners": ["note_author"],
        "additions": ["change_diff"],
        "deletions": ["change_diff"],
        "comments": ["discussion_notes", "note_body"],
    },
}

DEFAULT_PLATFORM_METRICS = {
    "github": [
        "pr_title",
        "pr_description",
        "pr_number",
        "pr_status",
        "pr_state",
        "pr_author",
        "pr_creation_date",
        "pr_merge_date",
        "pr_close_date",
        "pr_merged_by",
        "commit_sha",
        "commit_message",
        "commit_author",
        "commit_date",
        "commit_changes",
        "pr_comments",
        "pr_comment_author",
        "pr_comment_date",
        "pr_comment_body",
        "review_state",
        "review_author",
        "review_date",
        "review_body",
        "review_comment_body",
        "review_comment_author",
        "review_comment_date",
        "review_comment_position",
        "review_comment_path",
        "file_name",
        "file_status",
        "file_additions",
        "file_deletions",
        "file_changes",
    ],
    "gitlab": [
        "mr_title",
        "mr_description",
        "mr_iid",
        "mr_status",
        "mr_state",
        "mr_author",
        "mr_creation_date",
        "mr_merge_date",
        "mr_close_date",
        "mr_merged_by",
        "commit_id",
        "commit_message",
        "commit_author",
        "commit_date",
        "commit_changes",
        "discussion_id",
        "discussion_notes",
        "discussion_resolved",
        "note_body",
        "note_author",
        "note_date",
        "note_type",
        "change_old_path",
        "change_new_path",
        "change_diff",
        "change_new_file",
        "change_renamed_file",
        "change_deleted_file",
    ],
}


def sanitize_user_prompt(prompt: Any) -> str:
    """Trim user prompt, remove control characters, and cap payload size."""
    if not isinstance(prompt, str):
        raise CollectionAutomationValidationError("prompt must be a string")

    sanitized = re.sub(r"[\x00-\x08\x0B-\x1F\x7F]", " ", prompt)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()

    if not sanitized:
        raise CollectionAutomationValidationError("prompt is required")

    if len(sanitized) > MAX_PROMPT_LENGTH:
        raise CollectionAutomationValidationError(
            f"prompt must be at most {MAX_PROMPT_LENGTH} characters"
        )

    return sanitized


def build_llm_collection_prompt(repository_details: dict, user_prompt: str) -> str:
    """Provide repository context so the model drafts collection filters for the correct repo."""
    platform = repository_details.get("platform", "github")
    return (
        "Repository context:\n"
        f"- Platform: {platform}\n"
        f"- Repository: {repository_details.get('full_name') or repository_details.get('name')}\n"
        f"- Default branch: {repository_details.get('default_branch') or 'unknown'}\n"
        "Task:\n"
        "- Interpret the request strictly as a data collection and cleaning configuration draft.\n"
        "- Return only the JSON schema for collection intent.\n"
        f"User request:\n{user_prompt}"
    )


def normalize_collection_automation_payload(
    llm_payload: dict[str, Any],
    repository_details: dict[str, Any],
    available_branches: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate and normalize an LLM response into the collection service payload shape."""
    if not isinstance(llm_payload, dict):
        raise CollectionAutomationValidationError("LLM response must be a JSON object")

    result = llm_payload.get("result")
    if not isinstance(result, dict):
        raise CollectionAutomationValidationError("LLM response is missing a valid result object")

    intent = _normalize_identifier(result.get("intent"))
    if intent != "collect":
        raise CollectionAutomationValidationError(
            f"LLM returned unsupported intent '{result.get('intent')}'"
        )

    warnings: list[str] = []

    repository_platform = _normalize_platform(repository_details.get("platform"))
    requested_platform = _normalize_platform(result.get("platform"))
    platform = repository_platform or requested_platform or "github"
    if requested_platform and repository_platform and requested_platform != repository_platform:
        warnings.append(
            f"Platform '{requested_platform}' was ignored because the repository is configured as '{repository_platform}'."
        )

    collection_filters = result.get("basic_filters")
    collection_filters = collection_filters if isinstance(collection_filters, dict) else {}
    start_date, end_date = _normalize_date_range(
        collection_filters.get("date_range"),
        field_name="basic_filters.date_range",
    )
    statuses = _normalize_statuses(collection_filters.get("pr_status"))
    branch_name = _normalize_branch(
        result.get("branch"),
        available_branches or [],
        repository_details.get("default_branch"),
        warnings,
    )

    selected_features = _normalize_features(result.get("features"), warnings)
    selected_metrics = _normalize_metrics(result.get("metrics"), platform, warnings)
    if not selected_metrics and result.get("metrics") in (None, [], ""):
        selected_metrics = DEFAULT_PLATFORM_METRICS.get(platform, []).copy()
        if selected_metrics:
            warnings.append(
                "No collection metrics were generated, so all available metrics were selected by default."
            )
    selected_metrics = _append_required_feature_metrics(
        selected_metrics,
        selected_features,
        platform,
        warnings,
    )

    if not selected_metrics:
        raise CollectionAutomationValidationError(
            "The generated draft did not include any valid collection metrics."
        )

    cleaning_filters = result.get("cleaning_filters")
    cleaning_filters = cleaning_filters if isinstance(cleaning_filters, dict) else {}
    cleaning_start, cleaning_end = _normalize_date_range(
        cleaning_filters.get("refined_date_range"),
        field_name="cleaning_filters.refined_date_range",
        allow_null=True,
    )

    if start_date and cleaning_start and cleaning_start < start_date:
        warnings.append(
            "Cleaning start date is earlier than the collection start date and may produce an empty subset."
        )
    if end_date and cleaning_end and cleaning_end > end_date:
        warnings.append(
            "Cleaning end date is later than the collection end date and may produce an empty subset."
        )

    normalized = {
        "model": llm_payload.get("model") or DEFAULT_LLM_MODEL,
        "warnings": warnings,
        "draft": {
            "collection": {
                "platform": platform,
                "branch_name": branch_name,
                "selected_metrics": selected_metrics,
                "start_date": start_date,
                "end_date": end_date,
                "status": statuses,
            },
            "cleaning": {
                "start_date": cleaning_start,
                "end_date": cleaning_end,
                "filters": {
                    "file_extensions": _normalize_file_extensions(
                        cleaning_filters.get("file_extensions"),
                        warnings,
                    ),
                    "authors": _normalize_string_list(
                        cleaning_filters.get("authors"),
                        label="authors",
                        warnings=warnings,
                    ),
                    "keyword_filters": _normalize_keyword_filters(
                        cleaning_filters.get("keywords"),
                        warnings,
                    ),
                },
                "selected_features": selected_features,
            },
        },
        "repository": {
            "name": repository_details.get("name"),
            "full_name": repository_details.get("full_name"),
            "platform": platform,
            "default_branch": repository_details.get("default_branch"),
        },
    }

    logger.info(
        "Normalized automation draft for repository=%s platform=%s warnings=%s metrics=%s features=%s",
        repository_details.get("full_name") or repository_details.get("name"),
        platform,
        len(warnings),
        len(selected_metrics),
        len(selected_features),
    )

    return normalized


def build_collection_automation_debug_context(llm_payload: Any) -> dict[str, Any]:
    """Extract safe debug fields from the LLM payload for error responses and logs."""
    if not isinstance(llm_payload, dict):
        return {"llm_payload_type": type(llm_payload).__name__}

    result = llm_payload.get("result")
    if not isinstance(result, dict):
        return {
            "llm_model": llm_payload.get("model"),
            "llm_result_type": type(result).__name__,
        }

    return {
        "llm_model": llm_payload.get("model"),
        "llm_intent": result.get("intent"),
        "llm_platform": result.get("platform"),
        "llm_branch": result.get("branch"),
        "llm_metrics": result.get("metrics"),
        "llm_features": result.get("features"),
    }


def _normalize_platform(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = _normalize_identifier(value)
    if normalized in {"gitlab_self", "gitlabself"}:
        return "gitlab"
    if normalized in {"github", "gitlab"}:
        return normalized
    return None


def _normalize_date_range(
    raw_range: Any,
    *,
    field_name: str,
    allow_null: bool = True,
) -> tuple[str | None, str | None]:
    if raw_range in (None, "", {}):
        if allow_null:
            return None, None
        raise CollectionAutomationValidationError(f"{field_name} is required")

    if not isinstance(raw_range, dict):
        raise CollectionAutomationValidationError(f"{field_name} must be an object")

    start_date = _parse_iso_date(raw_range.get("start_date"), f"{field_name}.start_date")
    end_date = _parse_iso_date(raw_range.get("end_date"), f"{field_name}.end_date")

    if start_date and end_date and end_date < start_date:
        raise CollectionAutomationValidationError(f"{field_name} end_date must be after start_date")

    return (
        start_date.isoformat() if start_date else None,
        end_date.isoformat() if end_date else None,
    )


def _parse_iso_date(value: Any, field_name: str) -> date | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise CollectionAutomationValidationError(f"{field_name} must be a string in YYYY-MM-DD format")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise CollectionAutomationValidationError(
            f"{field_name} must be a valid date in YYYY-MM-DD format"
        ) from exc


def _normalize_statuses(raw_statuses: Any) -> list[str]:
    if raw_statuses in (None, ""):
        return DEFAULT_COLLECTION_STATUSES.copy()

    if not isinstance(raw_statuses, list):
        raise CollectionAutomationValidationError("basic_filters.pr_status must be a list")

    normalized_statuses: list[str] = []
    for status in raw_statuses:
        if not isinstance(status, str):
            raise CollectionAutomationValidationError("Each status must be a string")
        normalized = _normalize_identifier(status)
        if normalized == "opened":
            normalized = "open"
        if normalized not in {"open", "closed", "merged"}:
            raise CollectionAutomationValidationError(
                f"Unsupported collection status '{status}'"
            )
        if normalized not in normalized_statuses:
            normalized_statuses.append(normalized)

    return normalized_statuses or DEFAULT_COLLECTION_STATUSES.copy()


def _normalize_branch(
    raw_branch: Any,
    available_branches: list[dict[str, Any]],
    default_branch: str | None,
    warnings: list[str],
) -> str | None:
    branch_names = {
        branch.get("name")
        for branch in available_branches
        if isinstance(branch, dict) and branch.get("name")
    }

    candidate: str | None = None
    if isinstance(raw_branch, str):
        candidate = raw_branch.strip() or None
    elif isinstance(raw_branch, list):
        for branch in raw_branch:
            if isinstance(branch, str) and branch.strip():
                candidate = branch.strip()
                break
    elif raw_branch not in (None, ""):
        warnings.append("Generated branch selection had an unsupported format and was ignored.")

    if candidate and branch_names and candidate not in branch_names:
        warnings.append(
            f"Branch '{candidate}' is not available for this repository. The default branch will be used instead."
        )
        candidate = None

    return candidate or default_branch


def _normalize_metrics(
    raw_metrics: Any,
    platform: str,
    warnings: list[str],
) -> list[str]:
    if raw_metrics in (None, ""):
        return []
    if not isinstance(raw_metrics, list):
        raise CollectionAutomationValidationError("metrics must be a list")

    aliases = PLATFORM_METRIC_ALIASES.get(platform, {})
    normalized_metrics: list[str] = []
    invalid_metrics: list[str] = []

    for metric in raw_metrics[:MAX_LIST_ITEMS]:
        if not isinstance(metric, str):
            invalid_metrics.append(str(metric))
            continue
        normalized = aliases.get(_normalize_identifier(metric))
        if not normalized:
            invalid_metrics.append(metric)
            continue
        if normalized not in normalized_metrics:
            normalized_metrics.append(normalized)

    if invalid_metrics:
        warnings.append(
            "Ignored unsupported metrics: " + ", ".join(invalid_metrics[:10])
        )

    return normalized_metrics


def _normalize_features(raw_features: Any, warnings: list[str]) -> list[str]:
    if raw_features in (None, ""):
        return []
    if not isinstance(raw_features, list):
        raise CollectionAutomationValidationError("features must be a list")

    normalized_features: list[str] = []
    invalid_features: list[str] = []

    for feature in raw_features[:MAX_LIST_ITEMS]:
        if not isinstance(feature, str):
            invalid_features.append(str(feature))
            continue
        normalized = FEATURE_ALIASES.get(_normalize_identifier(feature))
        if not normalized:
            invalid_features.append(feature)
            continue
        if normalized not in normalized_features:
            normalized_features.append(normalized)

    if invalid_features:
        warnings.append(
            "Ignored unsupported cleaning features: "
            + ", ".join(invalid_features[:10])
        )

    return normalized_features


def _append_required_feature_metrics(
    metrics: list[str],
    features: list[str],
    platform: str,
    warnings: list[str],
) -> list[str]:
    required_metrics: list[str] = []
    dependency_map = FEATURE_DEPENDENCIES.get(platform, {})

    for feature in features:
        for metric in dependency_map.get(feature, []):
            if metric not in metrics and metric not in required_metrics:
                required_metrics.append(metric)

    if required_metrics:
        warnings.append(
            "Added metrics required by the selected cleaning features: "
            + ", ".join(required_metrics)
        )

    return metrics + required_metrics


def _normalize_file_extensions(raw_extensions: Any, warnings: list[str]) -> list[str]:
    normalized_extensions = _normalize_string_list(
        raw_extensions,
        label="file extensions",
        warnings=warnings,
    )
    normalized: list[str] = []
    for extension in normalized_extensions:
        ext = extension.lower().strip()
        if not ext:
            continue
        ext = ext if ext.startswith(".") else f".{ext}"
        if re.fullmatch(r"\.[a-z0-9_+-]+", ext) and ext not in normalized:
            normalized.append(ext)
        else:
            warnings.append(f"Ignored invalid file extension '{extension}'.")
    return normalized


def _normalize_keyword_filters(raw_keywords: Any, warnings: list[str]) -> list[dict[str, Any]]:
    if raw_keywords in (None, "", {}):
        return []

    if not isinstance(raw_keywords, dict):
        raise CollectionAutomationValidationError("cleaning_filters.keywords must be an object")

    raw_fields = raw_keywords.get("fields")
    raw_terms = raw_keywords.get("terms")
    fields = _normalize_string_list(raw_fields, label="keyword fields", warnings=warnings)
    terms = _normalize_string_list(raw_terms, label="keyword terms", warnings=warnings)

    normalized_fields: list[str] = []
    invalid_fields: list[str] = []
    for field in fields:
        normalized = VALID_KEYWORD_FIELDS.get(_normalize_identifier(field))
        if normalized and normalized not in normalized_fields:
            normalized_fields.append(normalized)
        elif not normalized:
            invalid_fields.append(field)

    if invalid_fields:
        warnings.append(
            "Ignored unsupported keyword fields: " + ", ".join(invalid_fields[:10])
        )

    if not normalized_fields or not terms:
        return []

    return [{"field": field, "keywords": terms} for field in normalized_fields]


def _normalize_string_list(
    raw_values: Any,
    *,
    label: str,
    warnings: list[str],
) -> list[str]:
    if raw_values in (None, ""):
        return []
    if not isinstance(raw_values, list):
        raise CollectionAutomationValidationError(f"{label} must be a list")

    normalized: list[str] = []
    for value in raw_values[:MAX_LIST_ITEMS]:
        if not isinstance(value, str):
            warnings.append(f"Ignored non-string value in {label}.")
            continue
        cleaned = value.strip()
        if not cleaned:
            continue
        cleaned = cleaned[:MAX_STRING_LENGTH]
        if cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


def _normalize_identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
