"""Unit tests for the domain layer.

Tests cover:
- Metric configuration helpers (``collectors.domain.entities.metrics_config``)
- Streaming metadata extraction (``collectors.domain.processors.metadata_extractor``)
"""
import io
import json
import pytest

from collectors.domain.entities.metrics_config import (
    GITHUB_METRICS,
    GITLAB_METRICS,
    get_metrics_for_platform,
    get_required_endpoints,
)
from collectors.domain.processors.metadata_extractor import (
    extract_cleaning_metadata,
    _ReplayStream,
)


# =============================================================================
# Metrics config
# =============================================================================

class TestGetMetricsForPlatform:
    def test_github_returns_dict_of_categories(self):
        metrics = get_metrics_for_platform("github")
        # Returns a dict keyed by category name
        assert isinstance(metrics, dict)
        assert len(metrics) > 0
        # Each category value must be a list of dicts with value/label keys
        for category, items in metrics.items():
            assert isinstance(items, list)
            for m in items:
                assert "value" in m
                assert "label" in m

    def test_gitlab_returns_dict_of_categories(self):
        metrics = get_metrics_for_platform("gitlab")
        assert isinstance(metrics, dict)
        assert len(metrics) > 0
        for category, items in metrics.items():
            for m in items:
                assert "value" in m and "label" in m

    def test_gitlab_self_same_as_gitlab(self):
        assert get_metrics_for_platform("gitlab_self") == get_metrics_for_platform("gitlab")

    def test_unknown_platform_returns_empty_dict(self):
        result = get_metrics_for_platform("unknown_platform")
        # Returns an empty dict for unknown platforms — never raises
        assert isinstance(result, dict)
        assert len(result) == 0


class TestGetRequiredEndpoints:
    def test_github_pr_title_needs_details(self):
        # 'pr_title' is in 'Pull Request Metadata' category → maps to 'details'
        endpoints = get_required_endpoints("github", ["pr_title"])
        assert isinstance(endpoints, set)
        assert "details" in endpoints

    def test_github_commit_sha_needs_commits(self):
        endpoints = get_required_endpoints("github", ["commit_sha"])
        assert "commits" in endpoints
        assert "details" in endpoints  # 'details' is always included

    def test_empty_metrics_returns_empty_set(self):
        """With no metrics selected, returns an empty set."""
        result = get_required_endpoints("github", [])
        assert isinstance(result, set)
        assert len(result) == 0

    def test_gitlab_note_body_needs_notes(self):
        endpoints = get_required_endpoints("gitlab", ["note_body"])
        assert isinstance(endpoints, set)
        assert "notes" in endpoints
        assert "details" in endpoints  # always included


# =============================================================================
# _ReplayStream
# =============================================================================

class TestReplayStream:
    def test_replays_prefix_then_continues(self):
        prefix = b"{"
        rest = io.BytesIO(b'"key": 1}')
        stream = _ReplayStream(prefix, rest)
        result = stream.read(10)
        assert result == b'{"key": 1}'

    def test_read_all(self):
        prefix = b"ab"
        rest = io.BytesIO(b"cd")
        stream = _ReplayStream(prefix, rest)
        assert stream.read() == b"abcd"


# =============================================================================
# extract_cleaning_metadata
# =============================================================================

def _make_github_stream(prs):
    """Helper: build a bytes stream of {"pull_requests": [...]} JSON."""
    data = {"pull_requests": prs}
    return io.BytesIO(json.dumps(data).encode())


def _make_gitlab_stream(mrs):
    data = {"merge_requests": mrs}
    return io.BytesIO(json.dumps(data).encode())


def _github_pr(author="alice", extensions=(".py",)):
    files = [{"filename": f"module{ext}"} for ext in extensions]
    return {
        "details": {"user": {"login": author}},
        "files": files,
    }


def _gitlab_mr(author="bob", extensions=(".py",)):
    files = [{"new_path": f"module{ext}"} for ext in extensions]
    return {
        "details": {"author": {"username": author}},
        "changes": {"changes": files},
    }


class TestExtractCleaningMetadata:
    def test_github_extracts_authors_and_extensions(self):
        prs = [
            _github_pr("alice", [".py", ".md"]),
            _github_pr("bob", [".py", ".js"]),
        ]
        meta = extract_cleaning_metadata(_make_github_stream(prs), "github")
        assert set(meta["authors"]) == {"alice", "bob"}
        assert ".py" in meta["file_extensions"]
        assert ".md" in meta["file_extensions"]
        assert meta["total_items"] == 2

    def test_gitlab_extracts_authors_and_extensions(self):
        mrs = [_gitlab_mr("carol", [".rb"]), _gitlab_mr("dave", [".go"])]
        meta = extract_cleaning_metadata(_make_gitlab_stream(mrs), "gitlab")
        assert set(meta["authors"]) == {"carol", "dave"}
        assert ".rb" in meta["file_extensions"]
        assert meta["total_items"] == 2

    def test_list_format_github(self):
        """Handles bare list format (external upload)."""
        prs = [_github_pr("eve", [".ts"])]
        stream = io.BytesIO(json.dumps(prs).encode())
        meta = extract_cleaning_metadata(stream, "github")
        assert meta["total_items"] == 1
        assert "eve" in meta["authors"]

    def test_empty_stream_returns_zeros(self):
        stream = io.BytesIO(b"{}")
        meta = extract_cleaning_metadata(stream, "github")
        assert meta["total_items"] == 0
        assert meta["authors"] == []

    def test_authors_sorted(self):
        prs = [_github_pr("zoe"), _github_pr("anna"), _github_pr("mike")]
        meta = extract_cleaning_metadata(_make_github_stream(prs), "github")
        assert meta["authors"] == sorted(meta["authors"])

    def test_file_extensions_sorted(self):
        prs = [_github_pr("x", [".rb", ".go", ".py"])]
        meta = extract_cleaning_metadata(_make_github_stream(prs), "github")
        assert meta["file_extensions"] == sorted(meta["file_extensions"])
