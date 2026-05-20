"""Automatic collection draft generation."""

from __future__ import annotations

import os
import re
from typing import Any

import requests

from collectors.domain.entities.metrics_config import get_all_metric_values
from collectors.services import (
    CollectionServiceError,
    CollectionValidationError,
    resolve_repository_metadata,
)


DEFAULT_STATUSES = ["open", "closed", "merged"]
VALID_STATUSES = set(DEFAULT_STATUSES)

FEATURE_ALIASES = {
    "creation_date": "Creation_Date",
    "commits_count": "#Commits",
    "commit_count": "#Commits",
    "discussions_count": "#Discussions",
    "discussion_count": "#Discussions",
    "lead_time": "Lead_Time",
    "mean_time_between_commits": "Mean_Time_between_commits",
    "committers_list": "Commiters",
    "commiters_list": "Commiters",
    "committer_names": "Commiter_Names",
    "commiters_names": "Commiter_Names",
    "unique_committers": "#UniqueCommiters",
    "unique_commiters": "#UniqueCommiters",
    "minor_authors": "nb_minor_author",
    "major_authors": "nb_major_author",
    "delta_time": "delta_time",
    "churn_additions": "churn_addition",
    "churn_deletions": "churn_deletions",
    "initial_size": "initial_size",
    "historical_entropy": "hist_entropy",
    "modified_files": "modified_files",
    "file_types": "filetypes",
    "state": "state",
    "rework_size": "rework_size",
    "author": "Author",
    "reviewers": "Reviewers",
    "reviewers_count": "#reviewers",
    "people_count": "#people",
    "committers_count": "#commiters",
    "commiters_count": "#commiters",
    "discussers_count": "#discussionners",
    "discussionners_count": "#discussionners",
    "comments_count": "comments",
    "total_additions": "additions",
    "total_deletions": "deletions",
    "merged_at": "merged_at",
}

METRIC_ALIASES = {
    "github": {
        "creation_date": "pr_creation_date",
        "merge_date": "pr_merge_date",
        "close_date": "pr_close_date",
        "merged_by": "pr_merged_by",
        "commit_messages": "commit_message",
        "commit_authors": "commit_author",
        "commit_dates": "commit_date",
        "file_changes": "commit_changes",
        "comment_authors": "pr_comment_author",
        "comment_dates": "pr_comment_date",
        "comment_content": "pr_comment_body",
        "reviewer": "review_author",
        "review_comments": "review_body",
        "inline_comments": "review_comment_body",
        "comment_author": "review_comment_author",
        "comment_date": "review_comment_date",
        "code_position": "review_comment_position",
        "file_path": "review_comment_path",
        "file_names": "file_name",
        "lines_added": "file_additions",
        "lines_deleted": "file_deletions",
        "total_changes": "file_changes",
    },
    "gitlab": {
        "creation_date": "mr_creation_date",
        "merge_date": "mr_merge_date",
        "close_date": "mr_close_date",
        "merged_by": "mr_merged_by",
        "commit_messages": "commit_message",
        "commit_authors": "commit_author",
        "commit_dates": "commit_date",
        "file_changes_diff": "commit_changes",
        "note_content": "note_body",
        "old_file_path": "change_old_path",
        "new_file_path": "change_new_path",
        "file_diff": "change_diff",
        "new_file": "change_new_file",
        "renamed_file": "change_renamed_file",
        "deleted_file": "change_deleted_file",
    },
}

FEATURE_DEPENDENCIES = {
    "Creation_Date": {
        "github": ["pr_creation_date"],
        "gitlab": ["mr_creation_date"],
    },
    "Lead_Time": {
        "github": ["pr_creation_date", "pr_merge_date", "pr_state"],
        "gitlab": ["mr_creation_date", "mr_merge_date", "mr_state"],
    },
    "#Commits": {
        "github": ["commit_sha"],
        "gitlab": ["commit_id"],
    },
    "Mean_Time_between_commits": {
        "github": ["commit_date"],
        "gitlab": ["commit_date"],
    },
    "Commiters": {
        "github": ["commit_author"],
        "gitlab": ["commit_author"],
    },
    "Commiter_Names": {
        "github": ["commit_author"],
        "gitlab": ["commit_author"],
    },
    "#UniqueCommiters": {
        "github": ["commit_author"],
        "gitlab": ["commit_author"],
    },
    "#Discussions": {
        "github": ["pr_comments"],
        "gitlab": ["discussion_notes"],
    },
    "comments": {
        "github": ["pr_comments", "pr_comment_body"],
        "gitlab": ["note_body"],
    },
    "Reviewers": {
        "github": ["review_author"],
        "gitlab": ["discussion_notes"],
    },
    "#reviewers": {
        "github": ["review_author"],
        "gitlab": ["discussion_notes"],
    },
    "churn_addition": {
        "github": ["file_additions"],
        "gitlab": ["change_diff"],
    },
    "churn_deletions": {
        "github": ["file_deletions"],
        "gitlab": ["change_diff"],
    },
    "additions": {
        "github": ["file_additions"],
        "gitlab": ["change_diff"],
    },
    "deletions": {
        "github": ["file_deletions"],
        "gitlab": ["change_diff"],
    },
    "modified_files": {
        "github": ["file_name", "file_status"],
        "gitlab": ["change_new_path", "change_old_path"],
    },
    "filetypes": {
        "github": ["file_name"],
        "gitlab": ["change_new_path"],
    },
    "hist_entropy": {
        "github": ["file_name", "file_changes"],
        "gitlab": ["change_new_path", "change_diff"],
    },
    "state": {
        "github": ["pr_state"],
        "gitlab": ["mr_state"],
    },
    "Author": {
        "github": ["pr_author"],
        "gitlab": ["mr_author"],
    },
    "merged_at": {
        "github": ["pr_merge_date"],
        "gitlab": ["mr_merge_date"],
    },
}

DEFAULT_METRICS = {
    "github": ["pr_title", "pr_author", "pr_creation_date", "pr_state"],
    "gitlab": ["mr_title", "mr_author", "mr_creation_date", "mr_state"],
}


def _key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_")


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        return [value]
    return []


def _clean_date(value: Any) -> str | None:
    if not value:
        return None
    match = re.match(r"^(\d{4}-\d{2}-\d{2})", str(value))
    return match.group(1) if match else None


def _platform_key(platform: str) -> str:
    return "gitlab" if platform in {"gitlab", "gitlab_self"} else "github"


def _normalize_metric(metric: Any, platform: str, available: set[str]) -> str | None:
    raw = str(metric or "").strip()
    if raw in available:
        return raw

    platform_aliases = METRIC_ALIASES.get(_platform_key(platform), {})
    alias = platform_aliases.get(_key(raw))
    if alias in available:
        return alias

    return None


def _normalize_features(features: Any) -> list[str]:
    normalized = []
    for feature in _as_list(features):
        feature_id = FEATURE_ALIASES.get(_key(feature))
        if feature_id and feature_id not in normalized:
            normalized.append(feature_id)
    return normalized


def _normalize_statuses(value: Any) -> list[str]:
    statuses = []
    for status in _as_list(value):
        normalized = "open" if str(status).lower() == "opened" else str(status).lower()
        if normalized in VALID_STATUSES and normalized not in statuses:
            statuses.append(normalized)
    return statuses or DEFAULT_STATUSES.copy()


def _normalize_extensions(value: Any) -> list[str]:
    extensions = []
    for extension in _as_list(value):
        cleaned = str(extension or "").strip().lower()
        if not cleaned:
            continue
        if not cleaned.startswith("."):
            cleaned = f".{cleaned}"
        if cleaned not in extensions:
            extensions.append(cleaned)
    return extensions


def _normalize_keyword_filters(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, dict):
        return []

    terms = [
        str(term).strip()
        for term in _as_list(value.get("terms") or value.get("keywords"))
        if str(term).strip()
    ]
    if not terms:
        return []

    allowed_fields = {
        "title": "title",
        "description": "description",
        "comments": "comments",
        "comment": "comments",
        "commit": "commit_message",
        "commit_message": "commit_message",
        "commit_messages": "commit_message",
    }
    filters = []
    for field in _as_list(value.get("fields") or value.get("field") or ["title"]):
        normalized = allowed_fields.get(_key(field))
        if normalized and not any(item["field"] == normalized for item in filters):
            filters.append({"field": normalized, "keywords": terms})
    return filters


def _build_user_message(prompt: str, platform: str, repository: dict[str, Any]) -> str:
    metrics = get_all_metric_values(platform)
    return (
        "Generate a collection draft for this repository.\n"
        f"Repository: {repository['repository_full_name']}\n"
        f"Platform: {platform}\n"
        f"Default branch: {repository.get('default_branch') or 'main'}\n"
        f"Use only these metric values when possible: {', '.join(metrics)}\n"
        "Return JSON for intent=collect. User request:\n"
        f"{prompt}"
    )


class CollectionAutomationService:
    """Build a frontend-ready automatic collection draft."""

    @classmethod
    def generate_preview(cls, user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        prompt = str(payload.get("prompt") or "").strip()
        if not prompt:
            raise CollectionValidationError("prompt is required")

        workspace_id = payload.get("workspace_id")
        repository_id = payload.get("repository_id")
        if not workspace_id or not repository_id:
            raise CollectionValidationError("workspace_id and repository_id are required")

        try:
            repository = resolve_repository_metadata(
                user_id=user_id,
                workspace_id=int(workspace_id),
                repository_id=int(repository_id),
            )
        except (TypeError, ValueError) as exc:
            raise CollectionValidationError(
                "workspace_id and repository_id must be valid integers"
            ) from exc

        parsed = cls._call_llm(
            provider=payload.get("llm_provider") or "openrouter",
            model=payload.get("model"),
            user_message=_build_user_message(prompt, repository["platform"], repository),
        )

        draft, warnings = cls._build_draft(
            parsed=parsed,
            prompt=prompt,
            repository=repository,
        )
        return {
            "success": True,
            "provider": payload.get("llm_provider") or "openrouter",
            "model": payload.get("model"),
            "draft": draft,
            "warnings": warnings,
            "raw": parsed,
        }

    @staticmethod
    def _call_llm(provider: str, model: str | None, user_message: str) -> dict[str, Any]:
        selected_provider = provider if provider in {"openrouter", "ollama"} else "openrouter"
        base_url = os.getenv("LLM_SERVICE_URL", "http://llm-service:8004").rstrip("/")
        timeout = float(os.getenv("LLM_SERVICE_TIMEOUT", "75"))

        try:
            response = requests.post(
                f"{base_url}/{selected_provider}",
                json={"user_message": user_message, "model": model},
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise CollectionServiceError(f"LLM service unavailable: {exc}") from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise CollectionServiceError("LLM service returned a non-JSON response") from exc

        if response.status_code >= 400:
            detail = body.get("detail") or body.get("error") or body
            raise CollectionServiceError(f"LLM service error: {detail}")

        result = body.get("result")
        if not isinstance(result, dict):
            raise CollectionServiceError("LLM service response is missing a result object")

        return result

    @staticmethod
    def _build_draft(
        parsed: dict[str, Any],
        prompt: str,
        repository: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str]]:
        platform = repository["platform"]
        platform_key = _platform_key(platform)
        available = set(get_all_metric_values(platform))
        warnings = []

        if parsed.get("intent") and parsed.get("intent") != "collect":
            warnings.append(
                "The prompt looked more like analysis than collection, so a collection draft was inferred."
            )

        selected_metrics = []
        for metric in _as_list(parsed.get("metrics")):
            normalized = _normalize_metric(metric, platform, available)
            if normalized and normalized not in selected_metrics:
                selected_metrics.append(normalized)
            elif metric:
                warnings.append(f"Metric '{metric}' is not available for {platform}.")

        features = _normalize_features(parsed.get("features"))
        for feature in features:
            for metric in FEATURE_DEPENDENCIES.get(feature, {}).get(platform_key, []):
                if metric in available and metric not in selected_metrics:
                    selected_metrics.append(metric)

        if not selected_metrics:
            selected_metrics = [
                metric for metric in DEFAULT_METRICS[platform_key] if metric in available
            ]
            warnings.append(
                "No valid metric was detected, so a safe default metadata set was selected."
            )

        basic_filters = parsed.get("basic_filters") or {}
        date_range = basic_filters.get("date_range") or {}
        statuses = _normalize_statuses(
            basic_filters.get("pr_status")
            or basic_filters.get("mr_status")
            or basic_filters.get("status")
        )

        branch_values = _as_list(parsed.get("branch") or parsed.get("branches"))
        branch_name = str(branch_values[0]).strip() if branch_values else ""
        branch_name = branch_name or repository.get("default_branch") or "main"

        cleaning_filters = parsed.get("cleaning_filters") or {}
        refined_date_range = cleaning_filters.get("refined_date_range") or {}
        keyword_filters = _normalize_keyword_filters(
            cleaning_filters.get("keywords")
            or cleaning_filters.get("keyword_filters")
        )

        return (
            {
                "collection": {
                    "repository_id": repository["repository_id"],
                    "workspace_id": repository["workspace_id"],
                    "repository_full_name": repository["repository_full_name"],
                    "platform": platform,
                    "selected_metrics": selected_metrics,
                    "branch_name": branch_name,
                    "start_date": _clean_date(date_range.get("start_date")),
                    "end_date": _clean_date(date_range.get("end_date")),
                    "status": statuses,
                },
                "cleaning": {
                    "start_date": _clean_date(refined_date_range.get("start_date")),
                    "end_date": _clean_date(refined_date_range.get("end_date")),
                    "filters": {
                        "file_extensions": _normalize_extensions(
                            cleaning_filters.get("file_extensions")
                        ),
                        "authors": [
                            str(author).strip()
                            for author in _as_list(cleaning_filters.get("authors"))
                            if str(author).strip()
                        ],
                        "keyword_filters": keyword_filters,
                    },
                    "selected_features": features,
                },
                "prompt": prompt,
            },
            warnings,
        )
