import csv
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from collectors.infrastructure.exporters.csv_generator import (
    CSVGenerator,
    DataExtractor,
    GitHubDataExtractor,
    GitLabDataExtractor,
    MetricsCalculator,
    StatisticsCSVGenerator,
    get_data_extractor,
    get_platform_adapter,
)


def read_rows(csv_content):
    return list(csv.DictReader(csv_content.splitlines()))


class TestDataExtractors:
    def test_parse_iso_date_handles_empty_invalid_and_zulu(self):
        assert DataExtractor.parse_iso_date(None) is None
        assert DataExtractor.parse_iso_date("not-a-date") is None
        parsed = DataExtractor.parse_iso_date("2024-01-01T10:00:00Z")
        assert parsed == datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)

    def test_get_data_extractor_rejects_unknown_platform(self):
        with pytest.raises(ValueError, match="Unsupported platform"):
            get_data_extractor("bitbucket")

    def test_github_extracts_people_and_first_review_dates(self):
        item = {
            "comments": [
                {"created_at": "2024-01-03T00:00:00Z", "user": {"login": "commenter"}},
            ],
            "reviews": [
                {
                    "submitted_at": "2024-01-02T00:00:00Z",
                    "state": "APPROVED",
                    "user": {"login": "reviewer"},
                }
            ],
            "review_comments": [
                {"created_at": "2024-01-04T00:00:00Z", "user": {"login": "inline"}},
            ],
        }

        assert GitHubDataExtractor.get_first_review_date(item) == "2024-01-02T00:00:00Z"
        assert GitHubDataExtractor.get_first_formal_review_at(item) == "2024-01-02T00:00:00Z"
        assert GitHubDataExtractor.get_approved_at(item) == "2024-01-02T00:00:00Z"
        assert GitHubDataExtractor.count_human_comments(item) == 2
        assert GitHubDataExtractor.get_unique_discussioners(item) == {
            "commenter",
            "reviewer",
            "inline",
        }

    def test_gitlab_ignores_system_notes_and_deduplicates_human_comments(self):
        item = {
            "details": {
                "reviewers": [{"username": "reviewer"}],
            },
            "discussions": [
                {
                    "notes": [
                        {
                            "id": 1,
                            "system": "True",
                            "body": "approved this merge request",
                            "created_at": "2024-01-03T00:00:00Z",
                            "author": {"username": "bot"},
                        },
                        {
                            "id": 2,
                            "system": False,
                            "body": "please change this",
                            "created_at": "2024-01-02T00:00:00Z",
                            "author": {"username": "alice"},
                        },
                    ]
                }
            ],
            "notes": [
                {
                    "id": 2,
                    "system": False,
                    "body": "duplicate through notes endpoint",
                    "created_at": "2024-01-02T00:00:00Z",
                    "author": {"username": "alice"},
                },
                {
                    "id": 3,
                    "system": "1",
                    "body": "approved",
                    "created_at": "2024-01-01T00:00:00Z",
                    "author": {"username": "system"},
                },
            ],
        }

        assert GitLabDataExtractor.get_unique_reviewers(item) == {"reviewer"}
        assert GitLabDataExtractor.get_unique_discussioners(item) == {"alice"}
        assert GitLabDataExtractor.count_human_comments(item) == 1
        assert GitLabDataExtractor.get_first_review_date(item) == "2024-01-02T00:00:00Z"
        assert GitLabDataExtractor.get_approved_at(item) == "2024-01-01T00:00:00Z"

    def test_gitlab_diff_additions_and_deletions_ignore_headers(self):
        diff = "--- a/app.py\n+++ b/app.py\n-old\n+new\n+another"
        commit = {"changesHist": [{"diff": diff}]}
        file_change = {"new_path": "app.py", "diff": diff}

        assert GitLabDataExtractor.get_commit_additions(commit) == 2
        assert GitLabDataExtractor.get_commit_deletions(commit) == 1
        assert GitLabDataExtractor.get_file_additions(file_change) == 2
        assert GitLabDataExtractor.get_file_deletions(file_change) == 1


class TestMetricsCalculator:
    def test_metrics_edge_cases(self):
        assert MetricsCalculator.calculate_lead_time(None, None) == 0.0
        assert MetricsCalculator.calculate_mean_time_between_commits([]) == 0.0
        assert MetricsCalculator.calculate_entropy([0, 0]) == 0.0
        assert MetricsCalculator.calculate_author_contributions({}) == (0, 0)
        assert MetricsCalculator.calculate_time_diff_hours(
            datetime(2024, 1, 2, tzinfo=timezone.utc),
            datetime(2024, 1, 1, tzinfo=timezone.utc),
        ) is None

    def test_metrics_nominal_cases(self):
        t1 = datetime(2024, 1, 1, 10, tzinfo=timezone.utc)
        t2 = datetime(2024, 1, 1, 11, tzinfo=timezone.utc)
        t3 = datetime(2024, 1, 1, 13, tzinfo=timezone.utc)

        assert MetricsCalculator.calculate_lead_time(t1, t3) == 180.0
        assert MetricsCalculator.calculate_mean_time_between_commits([t3, t1, t2]) == 5400.0
        assert MetricsCalculator.calculate_churn([10, None, 3], [2, 0, 1]) == (13.0, 3.0)
        assert MetricsCalculator.calculate_author_contributions({"major": 99, "minor": 1}) == (1, 1)
        assert MetricsCalculator.calculate_delta_time(t2, t1) == round(1 / 24, 6)

    def test_rework_size_counts_commits_after_first_review(self):
        extractor = GitHubDataExtractor()
        commits = [
            {
                "details": {
                    "commit": {
                        "author": {"date": "2024-01-01T10:00:00Z"},
                    }
                },
                "changes": [{"additions": 10, "deletions": 1}],
            },
            {
                "details": {
                    "commit": {
                        "author": {"date": "2024-01-02T10:00:00Z"},
                    }
                },
                "changes": [{"additions": 5, "deletions": 2}],
            },
        ]
        first_review = DataExtractor.parse_iso_date("2024-01-02T00:00:00Z")

        assert MetricsCalculator.calculate_rework_size(commits, first_review, extractor) == 7.0


class TestCSVGenerator:
    def test_apply_filters_supports_extension_author_and_keyword_filters(self):
        generator = CSVGenerator("github")
        raw = {
            "project_created_at": "2024-01-01T00:00:00Z",
            "pull_requests": [
                {
                    "details": {
                        "title": "Fix authentication bug",
                        "user": {"login": "alice"},
                        "body": "important",
                    },
                    "files": [{"filename": "auth.py"}],
                    "comments": [{"body": "looks good"}],
                },
                {
                    "details": {
                        "title": "Docs",
                        "user": {"login": "bob"},
                        "body": "readme",
                    },
                    "files": [{"filename": "README.md"}],
                },
            ],
        }

        filtered = generator.apply_filters(
            raw,
            {
                "file_extensions": [".py"],
                "authors": ["alice"],
                "keyword_filters": [{"field": "title", "keywords": ["auth"]}],
            },
        )

        assert len(filtered["pull_requests"]) == 1
        assert filtered["project_created_at"] == raw["project_created_at"]

    def test_apply_filters_legacy_commit_message_keywords(self):
        generator = CSVGenerator("gitlab")
        raw = {
            "merge_requests": [
                {
                    "details": {"author": {"username": "alice"}},
                    "changes": {"diffs": [{"new_path": "app.py"}]},
                    "commits": [{"details": {"message": "fix parser"}}],
                }
            ]
        }

        filtered = generator.apply_filters(
            raw,
            {"keyword_field": "commit_message", "keywords": ["parser"]},
        )

        assert len(filtered["merge_requests"]) == 1

    def test_generate_csv_github_skips_malformed_items(self):
        generator = CSVGenerator("github")
        csv_content = generator.generate_csv(
            {
                "pull_requests": [
                    "bad item",
                    {
                        "details": {
                            "number": 1,
                            "title": "Fix",
                            "state": "closed",
                            "merged": True,
                            "created_at": "2024-01-01T00:00:00Z",
                            "merged_by": {"login": "maintainer"},
                            "user": {"login": "alice"},
                            "additions": 5,
                            "deletions": 2,
                        },
                        "commits": [{}],
                        "comments": [{}],
                        "reviews": [{}],
                        "review_comments": [{}],
                        "files": [{}],
                    },
                ]
            }
        )
        rows = read_rows(csv_content)

        assert rows[0]["PR_Number"] == "1"
        assert rows[0]["State"] == "merged"
        assert rows[0]["Additions"] == "5"

    def test_generate_csv_gitlab_counts_diff_lines(self):
        generator = CSVGenerator("gitlab")
        csv_content = generator.generate_csv(
            {
                "merge_requests": [
                    {
                        "details": {
                            "iid": 2,
                            "title": "MR",
                            "state": "merged",
                            "created_at": "bad-date",
                            "author": {"username": "alice"},
                            "merged_by": {"username": "bob"},
                        },
                        "commits": [{}, {}],
                        "notes": [{}],
                        "discussions": [{}],
                        "changes": {
                            "changes": [
                                {"diff": "--- a\n+++ b\n-old\n+new\n+extra"},
                            ]
                        },
                    }
                ]
            }
        )
        rows = read_rows(csv_content)

        assert rows[0]["MR_IID"] == "2"
        assert rows[0]["Additions"] == "2"
        assert rows[0]["Deletions"] == "1"
        assert rows[0]["Creation_Date"] == "bad-date"

    def test_get_preview_for_both_platforms(self):
        assert CSVGenerator("github").get_preview(
            {
                "pull_requests": [
                    {
                        "details": {
                            "number": 1,
                            "title": "PR",
                            "user": {"login": "alice"},
                            "state": "open",
                        },
                        "comments": [{}, {}],
                    }
                ]
            }
        )[0]["Comments"] == 2

        assert CSVGenerator("gitlab").get_preview(
            {
                "merge_requests": [
                    {
                        "details": {
                            "iid": 2,
                            "title": "MR",
                            "author": {"username": "bob"},
                            "state": "opened",
                        },
                        "notes": [{}],
                    }
                ]
            }
        )[0]["Notes"] == 1


class TestPlatformAdapters:
    def test_adapter_factory_and_unknown_platform(self):
        assert get_platform_adapter("github").get_item_key() == "pull_requests"
        assert get_platform_adapter("gitlab").get_item_key() == "merge_requests"
        with pytest.raises(ValueError, match="Unsupported platform"):
            get_platform_adapter("bitbucket")

    def test_github_adapter_tolerates_bad_shapes(self):
        adapter = get_platform_adapter("github")
        assert adapter.get_item_id("bad") is None
        assert adapter.get_files({"files": ["bad", {"filename": "ok.py"}]}) == [{"filename": "ok.py"}]
        assert adapter.get_additions("bad") == 0
        assert adapter.get_deletions("bad") == 0

    def test_gitlab_adapter_discussioners_ignore_system_notes(self):
        adapter = get_platform_adapter("gitlab")
        item = {
            "discussions": [
                {
                    "notes": [
                        {"system": "true", "author": {"username": "system"}},
                        {"system": "false", "author": {"username": "alice"}},
                    ]
                }
            ],
            "notes": [{"system": 0, "author": {"username": "bob"}}],
        }

        assert adapter.get_discussioners(item) == {"alice", "bob"}


class TestStatisticsCSVGenerator:
    def test_build_headers_uses_selected_features_and_platform_initial_size(self):
        github_headers = StatisticsCSVGenerator("github")._build_headers(
            ["Creation_Date", "initial_size", "comments"]
        )
        gitlab_headers = StatisticsCSVGenerator("gitlab")._build_headers(["initial_size"])

        assert github_headers == [
            "Project_ID",
            "PR_ID",
            "Creation_Date",
            "initial_pr_size",
            "comments",
        ]
        assert gitlab_headers == ["Project_ID", "MR_ID", "initial_mr_size"]

    def test_generate_statistics_csv_github_selected_features(self):
        generator = StatisticsCSVGenerator("github")
        plan = SimpleNamespace(repository_id=99)
        data = {
            "project_created_at": "2024-01-01T00:00:00Z",
            "pull_requests": [
                {
                    "details": {
                        "number": 10,
                        "title": "PR",
                        "state": "closed",
                        "merged": True,
                        "created_at": "2024-01-02T00:00:00Z",
                        "merged_at": "2024-01-03T00:00:00Z",
                        "closed_at": "2024-01-03T00:00:00Z",
                        "user": {"login": "alice"},
                        "additions": 10,
                        "deletions": 3,
                    },
                    "reviews": [
                        {
                            "state": "APPROVED",
                            "submitted_at": "2024-01-02T12:00:00Z",
                            "user": {"login": "reviewer"},
                        }
                    ],
                    "comments": [
                        {
                            "created_at": "2024-01-02T08:00:00Z",
                            "user": {"login": "commenter"},
                        }
                    ],
                    "review_comments": [],
                    "files": [{"filename": "app.py", "additions": 7, "deletions": 2}],
                    "commits": [
                        {
                            "details": {
                                "author": {"login": "alice"},
                                "commit": {
                                    "author": {
                                        "name": "Alice",
                                        "date": "2024-01-01T12:00:00Z",
                                    },
                                    "message": "initial",
                                },
                            },
                            "changes": [{"additions": 7, "deletions": 2}],
                        }
                    ],
                }
            ],
        }

        csv_content = generator.generate_statistics_csv(
            data,
            plan,
            selected_features=[
                "Lead_Time",
                "initial_size",
                "Author",
                "Reviewers",
                "filetypes",
                "pickup_time",
            ],
        )
        rows = read_rows(csv_content)

        assert rows[0]["Project_ID"] == "99"
        assert rows[0]["PR_ID"] == "10"
        assert rows[0]["Lead_Time"] == "1440.0"
        assert rows[0]["initial_pr_size"] == "9"
        assert rows[0]["Author"] == "alice"
        assert rows[0]["Reviewers"] == "reviewer"
        assert rows[0]["filetypes"] == "py"
        assert rows[0]["pickup_time"] == "12.0"

    def test_generate_statistics_csv_skips_malformed_items(self):
        generator = StatisticsCSVGenerator("github")
        plan = SimpleNamespace(repository_id=99)

        csv_content = generator.generate_statistics_csv(
            {"pull_requests": ["malformed"]},
            plan,
            selected_features=["Lead_Time"],
        )

        assert read_rows(csv_content) == []
