import pytest

from quality.infrastructure.etl.builder import build_dataset
from quality.infrastructure.etl.extractors import extract_hunk
from quality.models import Comment, Thread


@pytest.mark.django_db
class TestGitHubETL:
    def test_builds_clean_dataset(self, make_dataset, github_data):
        dataset = make_dataset(platform="github")
        stats = build_dataset(dataset, github_data)

        # categories (human only): general(bob) + review_summary(700) + inline(11,12)
        assert stats["by_category"] == {"general": 1, "review_summary": 1, "inline": 2}
        assert stats["comments_human"] == 4
        assert stats["comments_non_human"] == 1  # dependabot bot comment

        # role: alice authored the PR, so her inline reply is "author"; bob is reviewer
        assert stats["by_role"] == {"reviewer": 3, "author": 1}
        from quality.models import Comment as _C
        assert _C.objects.get(dataset=dataset, external_id="12").author_role == "author"
        assert _C.objects.get(dataset=dataset, external_id="11").author_role == "reviewer"

        # bot comment is stored but flagged non-human
        bot = Comment.objects.get(dataset=dataset, author="dependabot[bot]")
        assert bot.is_human is False and bot.author_is_bot is True

        # empty-body approval review (701) produces no comment
        assert not Comment.objects.filter(dataset=dataset, external_id="701").exists()

    def test_inline_thread_grouping_and_enrichment(self, make_dataset, github_data):
        dataset = make_dataset(platform="github")
        build_dataset(dataset, github_data)

        inline_threads = Thread.objects.filter(dataset=dataset, thread_type="inline")
        assert inline_threads.count() == 1
        thread = inline_threads.first()
        assert thread.is_resolved is True  # enriched from review_threads
        assert thread.comments.count() == 2  # 11 + reply 12 grouped

        c11 = Comment.objects.get(dataset=dataset, external_id="11")
        # reactions enriched from review_threads
        assert [(r.content, r.user) for r in c11.reactions.all()] == [("heart", "alice")]
        assert c11.got_reply is True  # reply 12 follows
        assert c11.is_resolved is True
        # commit on 2026-01-12 touches the file after the 2026-01-11 comment
        assert c11.code_changed_after is True

    def test_general_comment_reactions(self, make_dataset, github_data):
        dataset = make_dataset(platform="github")
        build_dataset(dataset, github_data)
        c = Comment.objects.get(dataset=dataset, external_id="900")
        assert c.comment_type == "general" and c.is_human is True
        assert [(r.content, r.user) for r in c.reactions.all()] == [("+1", "carol")]


@pytest.mark.django_db
class TestGitLabETL:
    def test_builds_clean_dataset(self, make_dataset, gitlab_data):
        dataset = make_dataset(platform="gitlab")
        stats = build_dataset(dataset, gitlab_data)

        assert stats["by_category"] == {"inline": 2, "general": 1}
        assert stats["comments_human"] == 3
        # the system note ("changed the description") is non-human
        assert stats["comments_non_human"] == 1
        # alice authored the MR; bob (9001 inline, 9010 general) is the reviewer
        assert stats["by_role"] == {"reviewer": 2, "author": 1}
        sysnote = Comment.objects.get(dataset=dataset, external_id="9011")
        assert sysnote.is_system is True and sysnote.is_human is False

    def test_inline_resolution_reactions_and_hunk(self, make_dataset, gitlab_data):
        dataset = make_dataset(platform="gitlab")
        build_dataset(dataset, gitlab_data)

        c = Comment.objects.get(dataset=dataset, external_id="9001")
        assert c.comment_type == "inline"
        assert c.is_resolved is True  # discussion.resolved
        assert c.got_reply is True  # 9002 follows
        assert c.code_changed_after is True
        # diff_hunk reconstructed from the changes diff
        assert "self._lock.acquire()" in c.diff_hunk
        assert [(r.content, r.user) for r in c.reactions.all()] == [("thumbsup", "carol")]


@pytest.mark.django_db
class TestCommitComments:
    def test_github_commit_comment_becomes_thread(self, make_dataset):
        data = {"pull_requests": [{
            "pull_request_number": 1,
            "details": {"number": 1, "user": {"login": "alice", "type": "User"},
                        "created_at": "2026-01-10T08:00:00Z"},
            "commit_comments": [
                {"id": 555, "user": {"login": "bob", "type": "User"}, "body": "nit on this commit",
                 "path": "a.py", "line": 10, "commit_id": "abc", "created_at": "2026-01-11T00:00:00Z"},
            ],
        }]}
        dataset = make_dataset(platform="github")
        stats = build_dataset(dataset, data)
        assert stats["by_category"].get("commit_comment") == 1
        c = Comment.objects.get(dataset=dataset, comment_type="commit_comment")
        assert c.author == "bob" and c.author_role == "reviewer" and c.path == "a.py"

    def test_gitlab_commit_discussion_becomes_thread(self, make_dataset):
        data = {"merge_requests": [{
            "merge_request_id": 17,
            "details": {"iid": 17, "author": {"username": "alice"}, "created_at": "2026-01-10T08:00:00Z"},
            "commit_comments": [
                {"commit_id": "abc", "discussions": [
                    {"id": "cd1", "resolved": None, "notes": [
                        {"id": 777, "system": False, "author": {"username": "bob"}, "body": "commit nit",
                         "created_at": "2026-01-11T00:00:00Z",
                         "position": {"new_path": "a.py", "new_line": 10}},
                    ]},
                ]},
            ],
        }]}
        dataset = make_dataset(platform="gitlab")
        stats = build_dataset(dataset, data)
        assert stats["by_category"].get("commit_comment") == 1
        c = Comment.objects.get(dataset=dataset, comment_type="commit_comment")
        assert c.author == "bob" and c.path == "a.py"


class TestExtractHunk:
    def test_finds_hunk_by_new_line(self):
        diff = (
            "@@ -1,3 +1,3 @@\n line a\n-old\n+new\n"
            "@@ -40,6 +40,8 @@ class X:\n     def acquire(self):\n+        self._lock.acquire()"
        )
        hunk = extract_hunk(diff, new_line=41, old_line=None)
        assert "self._lock.acquire()" in hunk
        assert "line a" not in hunk

    def test_empty_diff_returns_empty(self):
        assert extract_hunk("", 1, 1) == ""
