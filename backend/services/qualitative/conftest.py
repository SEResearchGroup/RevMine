"""Pytest fixtures for the qualitative service."""
import pytest
from rest_framework.test import APIClient

from quality.models import QualitativeDataset


@pytest.fixture
def make_dataset(db):
    def _make(platform="github", status="pending", user_id=1, **kw):
        defaults = dict(
            collection_id=1,
            user_id=user_id,
            workspace_id=1,
            repository_full_name="owner/repo",
            platform=platform,
            qualitative_data_filename="owner_repo.qualitative.json",
            status=status,
        )
        defaults.update(kw)
        return QualitativeDataset.objects.create(**defaults)
    return _make


@pytest.fixture
def api_client():
    client = APIClient()
    client.credentials(HTTP_X_USER_ID="1")
    return client


@pytest.fixture
def github_data():
    return {
        "project_created_at": "2025-01-01T00:00:00Z",
        "pull_requests": [
            {
                "pull_request_number": 1,
                "details": {
                    "number": 1, "title": "Fix race", "body": "desc",
                    "user": {"login": "alice", "type": "User"},
                    "state": "open", "merged": False,
                    "created_at": "2026-01-10T08:00:00Z",
                    "html_url": "https://gh/1", "additions": 10, "deletions": 2,
                    "changed_files": 1, "requested_reviewers": [{"login": "bob"}],
                },
                "commits": [{
                    "commit_sha": "s1",
                    "details": {"commit": {"committer": {"date": "2026-01-12T00:00:00Z"}}},
                    "changes": [{"filename": "src/worker_pool.py"}],
                }],
                "comments": [
                    {"id": 900, "user": {"login": "bob", "type": "User"}, "body": "Thanks!",
                     "created_at": "2026-01-10T09:00:00Z", "updated_at": "2026-01-10T09:00:00Z",
                     "reactions": [{"content": "+1", "user": {"login": "carol"}}]},
                    {"id": 901, "user": {"login": "dependabot[bot]", "type": "Bot"}, "body": "bump x",
                     "created_at": "2026-01-10T09:30:00Z", "reactions": []},
                ],
                "reviews": [
                    {"id": 700, "user": {"login": "bob", "type": "User"}, "state": "CHANGES_REQUESTED",
                     "submitted_at": "2026-01-11T10:00:00Z", "body": "Some remarks inline."},
                    {"id": 701, "user": {"login": "bob", "type": "User"}, "state": "APPROVED",
                     "submitted_at": "2026-01-12T10:00:00Z", "body": ""},
                ],
                "review_comments": [
                    {"id": 11, "user": {"login": "bob", "type": "User"}, "body": "why mutex?",
                     "diff_hunk": "@@ -40,6 +40,8 @@", "path": "src/worker_pool.py", "line": 42,
                     "original_line": 40, "side": "RIGHT", "created_at": "2026-01-11T10:05:00Z",
                     "updated_at": "2026-01-11T10:05:00Z", "in_reply_to_id": None,
                     "pull_request_review_id": 700},
                    {"id": 12, "user": {"login": "alice", "type": "User"}, "body": "because recursion",
                     "diff_hunk": "@@ -40,6 +40,8 @@", "path": "src/worker_pool.py", "line": 42,
                     "original_line": 40, "side": "RIGHT", "created_at": "2026-01-11T11:00:00Z",
                     "in_reply_to_id": 11},
                ],
                "review_threads": [
                    {"id": "PRRT1", "is_resolved": True, "is_outdated": False,
                     "path": "src/worker_pool.py", "line": 42, "original_line": 40, "side": "RIGHT",
                     "comments": [
                         {"id": 11, "reactions": [{"content": "heart", "user": "alice"}]},
                         {"id": 12, "reactions": []},
                     ]},
                ],
                "files": [{"filename": "src/worker_pool.py", "additions": 10, "deletions": 2}],
            }
        ],
    }


@pytest.fixture
def gitlab_data():
    return {
        "project_created_at": "2025-01-01T00:00:00Z",
        "merge_requests": [
            {
                "merge_request_id": 17,
                "details": {
                    "iid": 17, "title": "Fix race", "description": "d",
                    "author": {"username": "alice"}, "state": "merged",
                    "web_url": "https://gl/17", "created_at": "2026-01-10T08:00:00Z",
                    "reviewers": [{"username": "bob"}],
                },
                "commits": [{
                    "commit_id": "c1",
                    "details": {"committed_date": "2026-01-12T00:00:00Z"},
                    "changesHist": [{"new_path": "src/worker_pool.py", "old_path": "src/worker_pool.py"}],
                }],
                "discussions": [
                    {"id": "disc1", "resolved": True, "resolved_by": {"username": "alice"}, "notes": [
                        {"id": 9001, "system": False, "author": {"username": "bob"}, "body": "why mutex?",
                         "created_at": "2026-01-11T10:05:00Z", "updated_at": "2026-01-11T10:05:00Z",
                         "position": {"new_path": "src/worker_pool.py", "new_line": 42, "old_line": 40},
                         "award_emoji": [{"name": "thumbsup", "user": {"username": "carol"}}]},
                        {"id": 9002, "system": False, "author": {"username": "alice"}, "body": "because recursion",
                         "created_at": "2026-01-11T11:00:00Z",
                         "position": {"new_path": "src/worker_pool.py", "new_line": 42, "old_line": 40}},
                    ]},
                    {"id": "disc2", "resolved": None, "notes": [
                        {"id": 9010, "system": False, "author": {"username": "bob"}, "body": "Thanks!",
                         "created_at": "2026-01-10T09:00:00Z", "position": None},
                    ]},
                    {"id": "disc3", "resolved": None, "notes": [
                        {"id": 9011, "system": True, "author": {"username": "alice"},
                         "body": "changed the description", "created_at": "2026-01-10T09:30:00Z",
                         "position": None},
                    ]},
                ],
                "notes": [],
                "changes": {"changes": [{
                    "new_path": "src/worker_pool.py", "old_path": "src/worker_pool.py",
                    "diff": "@@ -40,6 +40,8 @@ class WorkerPool:\n     def acquire(self):\n+        self._lock.acquire()",
                }]},
            }
        ],
    }
