"""Platform-specific extraction of the qualitative JSON into a normalized,
platform-agnostic structure that the dataset builder persists.

Each extractor turns one collected project file into a list of ``review`` dicts:

    {
      "number", "title", "body", "author", "reviewers": [login, ...],
      "state", "url", "additions", "deletions", "changed_files",
      "created_at", "merged_at", "closed_at",
      "commit_changes": [(iso_date, [filenames]), ...],   # for the code-changed trace
      "threads": [
        {
          "external_id", "thread_type", "path",
          "is_resolved", "is_outdated", "resolved_by",
          "comments": [
            {
              "external_id", "author", "author_is_bot", "is_system", "body",
              "path", "line", "side", "diff_hunk", "reply_to_id",
              "created_at", "updated_at", "reactions": [{"content","user"}],
            }, ...
          ],
        }, ...
      ],
    }

The builder (builder.py) computes is_human, traces, denormalized fields and stats.
"""
from __future__ import annotations

import re

_BOT_LOGIN_RE = re.compile(r"(\[bot\]$|-bot$|^dependabot|^renovate|^github-actions)", re.IGNORECASE)


def _login_looks_like_bot(login: str) -> bool:
    return bool(login and _BOT_LOGIN_RE.search(login))


def _dig(d, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return cur if cur is not None else default


class GitHubExtractor:
    platform = "github"
    item_key = "pull_requests"

    def iter_reviews(self, data: dict) -> list[dict]:
        reviews = []
        for pr in data.get("pull_requests", []) or []:
            reviews.append(self._review(pr))
        return reviews

    def _review(self, pr: dict) -> dict:
        det = pr.get("details", {}) or {}
        number = pr.get("pull_request_number") or det.get("number")
        reviewers = [
            _dig(r, "login", default="")
            for r in (det.get("requested_reviewers") or [])
            if _dig(r, "login")
        ]
        state = "merged" if det.get("merged") else det.get("state", "")

        review = {
            "number": number,
            "title": det.get("title", "") or "",
            "body": det.get("body", "") or "",
            "author": _dig(det, "user", "login", default="") or "",
            "reviewers": reviewers,
            "state": state,
            "url": det.get("html_url", "") or "",
            "additions": det.get("additions"),
            "deletions": det.get("deletions"),
            "changed_files": det.get("changed_files"),
            "created_at": det.get("created_at"),
            "merged_at": det.get("merged_at"),
            "closed_at": det.get("closed_at"),
            "commit_changes": self._commit_changes(pr),
            "threads": [],
        }

        review["threads"].extend(self._general_threads(pr))
        review["threads"].extend(self._inline_threads(pr))
        review["threads"].extend(self._review_summary_threads(pr))
        review["threads"].extend(self._commit_comment_threads(pr))
        return review

    def _commit_comment_threads(self, pr: dict) -> list:
        """Comments left directly on a commit (GitHub commit comments)."""
        threads = []
        for c in pr.get("commit_comments", []) or []:
            login, is_bot = self._author_meta(c.get("user"))
            cid = str(c.get("id", ""))
            threads.append({
                "external_id": cid,
                "thread_type": "commit_comment",
                "path": c.get("path", "") or "",
                "is_resolved": None,
                "is_outdated": None,
                "resolved_by": "",
                "comments": [{
                    "external_id": cid,
                    "author": login,
                    "author_is_bot": is_bot,
                    "is_system": False,
                    "body": c.get("body", "") or "",
                    "path": c.get("path", "") or "",
                    "line": c.get("line"),
                    "side": "",
                    "diff_hunk": "",
                    "reply_to_id": "",
                    "created_at": c.get("created_at"),
                    "updated_at": c.get("updated_at"),
                    "reactions": [],
                }],
            })
        return threads

    def _commit_changes(self, pr: dict) -> list:
        out = []
        for c in pr.get("commits", []) or []:
            cd = c.get("details", {}) or {}
            date = (
                _dig(cd, "commit", "committer", "date")
                or _dig(cd, "commit", "author", "date")
            )
            files = [f.get("filename") for f in (c.get("changes") or []) if f.get("filename")]
            if date:
                out.append((date, files))
        return out

    def _author_meta(self, user: dict) -> tuple:
        login = _dig(user or {}, "login", default="") or ""
        is_bot = (_dig(user or {}, "type") == "Bot") or _login_looks_like_bot(login)
        return login, is_bot

    def _general_threads(self, pr: dict) -> list:
        threads = []
        for c in pr.get("comments", []) or []:
            login, is_bot = self._author_meta(c.get("user"))
            threads.append({
                "external_id": str(c.get("id", "")),
                "thread_type": "general",
                "path": "",
                "is_resolved": None,
                "is_outdated": None,
                "resolved_by": "",
                "comments": [{
                    "external_id": str(c.get("id", "")),
                    "author": login,
                    "author_is_bot": is_bot,
                    "is_system": False,
                    "body": c.get("body", "") or "",
                    "path": "",
                    "line": None,
                    "side": "",
                    "diff_hunk": "",
                    "reply_to_id": "",
                    "created_at": c.get("created_at"),
                    "updated_at": c.get("updated_at"),
                    "reactions": self._reactions(c.get("reactions")),
                }],
            })
        return threads

    def _review_summary_threads(self, pr: dict) -> list:
        threads = []
        for r in pr.get("reviews", []) or []:
            body = (r.get("body") or "").strip()
            if not body:
                continue  # empty verdicts carry no textual content
            login, is_bot = self._author_meta(r.get("user"))
            threads.append({
                "external_id": str(r.get("id", "")),
                "thread_type": "review_summary",
                "path": "",
                "is_resolved": None,
                "is_outdated": None,
                "resolved_by": "",
                "comments": [{
                    "external_id": str(r.get("id", "")),
                    "author": login,
                    "author_is_bot": is_bot,
                    "is_system": False,
                    "body": body,
                    "path": "",
                    "line": None,
                    "side": "",
                    "diff_hunk": "",
                    "reply_to_id": "",
                    "created_at": r.get("submitted_at"),
                    "updated_at": r.get("submitted_at"),
                    "reactions": [],
                }],
            })
        return threads

    def _inline_threads(self, pr: dict) -> list:
        """Primary source = review_comments (REST); enrich with review_threads
        (GraphQL) for resolution + reactions, keyed by comment id."""
        enrich = self._review_thread_index(pr)

        # Group review_comments into threads by reply-root id.
        groups: dict = {}
        order: list = []
        for c in pr.get("review_comments", []) or []:
            cid = c.get("id")
            root = c.get("in_reply_to_id") or cid
            key = str(root)
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(c)

        threads = []
        for key in order:
            comments = groups[key]
            first = comments[0]
            res = enrich.get("thread_by_comment", {}).get(str(first.get("id")), {})
            built = []
            for c in comments:
                login, is_bot = self._author_meta(c.get("user"))
                cid = str(c.get("id", ""))
                built.append({
                    "external_id": cid,
                    "author": login,
                    "author_is_bot": is_bot,
                    "is_system": False,
                    "body": c.get("body", "") or "",
                    "path": c.get("path", "") or "",
                    "line": c.get("line") if c.get("line") is not None else c.get("original_line"),
                    "side": c.get("side", "") or "",
                    "diff_hunk": c.get("diff_hunk", "") or "",
                    "reply_to_id": str(c.get("in_reply_to_id") or ""),
                    "created_at": c.get("created_at"),
                    "updated_at": c.get("updated_at"),
                    "reactions": enrich.get("reactions_by_comment", {}).get(cid, []),
                })
            threads.append({
                "external_id": key,
                "thread_type": "inline",
                "path": first.get("path", "") or "",
                "is_resolved": res.get("is_resolved"),
                "is_outdated": res.get("is_outdated"),
                "resolved_by": "",
                "comments": built,
            })
        return threads

    def _review_thread_index(self, pr: dict) -> dict:
        """Build lookups from review_threads (GraphQL enrichment): per-comment
        resolution (via the thread) and per-comment reactions."""
        thread_by_comment = {}
        reactions_by_comment = {}
        for t in pr.get("review_threads", []) or []:
            res = {"is_resolved": t.get("is_resolved"), "is_outdated": t.get("is_outdated")}
            for c in t.get("comments", []) or []:
                cid = str(c.get("id", ""))
                thread_by_comment[cid] = res
                if c.get("reactions"):
                    reactions_by_comment[cid] = self._reactions(c.get("reactions"))
        return {"thread_by_comment": thread_by_comment, "reactions_by_comment": reactions_by_comment}

    @staticmethod
    def _reactions(raw) -> list:
        out = []
        for r in raw or []:
            content = r.get("content")
            if not content:
                continue
            user = r.get("user")
            if isinstance(user, dict):
                user = user.get("login")
            out.append({"content": content, "user": user or ""})
        return out


class GitLabExtractor:
    platform = "gitlab"
    item_key = "merge_requests"

    def iter_reviews(self, data: dict) -> list[dict]:
        reviews = []
        for mr in data.get("merge_requests", []) or []:
            reviews.append(self._review(mr))
        return reviews

    def _review(self, mr: dict) -> dict:
        det = mr.get("details", {}) or {}
        number = mr.get("merge_request_id") or det.get("iid")
        reviewers = [
            _dig(r, "username", default="")
            for r in (det.get("reviewers") or [])
            if _dig(r, "username")
        ]
        file_diffs = self._file_diffs(mr)

        review = {
            "number": number,
            "title": det.get("title", "") or "",
            "body": det.get("description", "") or "",
            "author": _dig(det, "author", "username", default="") or "",
            "reviewers": reviewers,
            "state": det.get("state", "") or "",
            "url": det.get("web_url", "") or "",
            "additions": None,
            "deletions": None,
            "changed_files": len(file_diffs) or None,
            "created_at": det.get("created_at"),
            "merged_at": det.get("merged_at"),
            "closed_at": det.get("closed_at"),
            "commit_changes": self._commit_changes(mr),
            "threads": self._discussion_threads(mr, file_diffs),
        }
        review["threads"].extend(self._commit_comment_threads(mr))
        return review

    def _commit_comment_threads(self, mr: dict) -> list:
        """Discussions left directly on a commit (GitLab commit discussions)."""
        threads = []
        for entry in mr.get("commit_comments", []) or []:
            for disc in entry.get("discussions", []) or []:
                notes = disc.get("notes", []) or []
                if not notes:
                    continue
                first = notes[0]
                built = []
                for n in notes:
                    npos = n.get("position") or {}
                    login = _dig(n, "author", "username", default="") or ""
                    line = npos.get("new_line") if npos.get("new_line") is not None else npos.get("old_line")
                    built.append({
                        "external_id": str(n.get("id", "")),
                        "author": login,
                        "author_is_bot": _login_looks_like_bot(login),
                        "is_system": bool(n.get("system")),
                        "body": n.get("body", "") or "",
                        "path": npos.get("new_path") or npos.get("old_path") or "",
                        "line": line,
                        "side": "",
                        "diff_hunk": "",
                        "reply_to_id": "" if n is first else str(first.get("id", "")),
                        "created_at": n.get("created_at"),
                        "updated_at": n.get("updated_at"),
                        "reactions": self._reactions(n.get("award_emoji")),
                    })
                threads.append({
                    "external_id": str(disc.get("id", "")),
                    "thread_type": "commit_comment",
                    "path": (first.get("position") or {}).get("new_path", "") or "",
                    "is_resolved": disc.get("resolved"),
                    "is_outdated": None,
                    "resolved_by": _dig(disc, "resolved_by", "username", default="") or "",
                    "comments": built,
                })
        return threads

    def _file_diffs(self, mr: dict) -> dict:
        """Map new_path/old_path -> unified diff text from the changes endpoint."""
        diffs = {}
        changes = (mr.get("changes") or {})
        for ch in (changes.get("changes") or []):
            text = ch.get("diff") or ""
            for key in (ch.get("new_path"), ch.get("old_path")):
                if key:
                    diffs[key] = text
        return diffs

    def _commit_changes(self, mr: dict) -> list:
        out = []
        for c in mr.get("commits", []) or []:
            cd = c.get("details", {}) or {}
            date = cd.get("committed_date") or cd.get("authored_date") or cd.get("created_at")
            files = []
            for d in (c.get("changesHist") or []):
                for key in (d.get("new_path"), d.get("old_path")):
                    if key:
                        files.append(key)
            if date:
                out.append((date, files))
        return out

    def _discussion_threads(self, mr: dict, file_diffs: dict) -> list:
        threads = []
        for disc in mr.get("discussions", []) or []:
            notes = disc.get("notes", []) or []
            if not notes:
                continue
            first = notes[0]
            pos = first.get("position")
            is_inline = bool(pos)
            built = []
            for n in notes:
                npos = n.get("position") or {}
                login = _dig(n, "author", "username", default="") or ""
                is_system = bool(n.get("system"))
                is_bot = _login_looks_like_bot(login)
                line = npos.get("new_line") if npos.get("new_line") is not None else npos.get("old_line")
                diff_hunk = ""
                if npos:
                    path = npos.get("new_path") or npos.get("old_path") or ""
                    diff_hunk = extract_hunk(
                        file_diffs.get(path, ""),
                        npos.get("new_line"),
                        npos.get("old_line"),
                    )
                built.append({
                    "external_id": str(n.get("id", "")),
                    "author": login,
                    "author_is_bot": is_bot,
                    "is_system": is_system,
                    "body": n.get("body", "") or "",
                    "path": npos.get("new_path") or npos.get("old_path") or "",
                    "line": line,
                    "side": "",
                    "diff_hunk": diff_hunk,
                    "reply_to_id": "" if n is first else str(first.get("id", "")),
                    "created_at": n.get("created_at"),
                    "updated_at": n.get("updated_at"),
                    "reactions": self._reactions(n.get("award_emoji")),
                })
            threads.append({
                "external_id": str(disc.get("id", "")),
                "thread_type": "inline" if is_inline else "general",
                "path": (first.get("position") or {}).get("new_path", "") if is_inline else "",
                "is_resolved": disc.get("resolved"),
                "is_outdated": None,
                "resolved_by": _dig(disc, "resolved_by", "username", default="") or "",
                "comments": built,
            })
        return threads

    @staticmethod
    def _reactions(raw) -> list:
        out = []
        for a in raw or []:
            name = a.get("name")
            if not name:
                continue
            user = a.get("user")
            if isinstance(user, dict):
                user = user.get("username")
            out.append({"content": name, "user": user or ""})
        return out


_HUNK_HEADER_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def extract_hunk(diff_text: str, new_line, old_line) -> str:
    """Return the @@-hunk of a unified diff that contains the target line.

    Used to reconstruct a comment's diff hunk for GitLab (which, unlike GitHub,
    does not return a per-comment ``diff_hunk``). Best-effort: returns the whole
    matching hunk, or the first hunk / empty string if no match is found.
    """
    if not diff_text:
        return ""
    lines = diff_text.split("\n")
    hunks = []
    current = None
    for ln in lines:
        if ln.startswith("@@"):
            if current is not None:
                hunks.append(current)
            current = {"header": ln, "lines": [ln]}
        elif current is not None:
            current["lines"].append(ln)
    if current is not None:
        hunks.append(current)
    if not hunks:
        return ""

    target_new = new_line if isinstance(new_line, int) else None
    target_old = old_line if isinstance(old_line, int) else None

    for h in hunks:
        m = _HUNK_HEADER_RE.match(h["header"])
        if not m:
            continue
        old_start = int(m.group(1)); old_count = int(m.group(2) or 1)
        new_start = int(m.group(3)); new_count = int(m.group(4) or 1)
        if target_new is not None and new_start <= target_new < new_start + max(new_count, 1):
            return "\n".join(h["lines"])
        if target_old is not None and old_start <= target_old < old_start + max(old_count, 1):
            return "\n".join(h["lines"])

    return "\n".join(hunks[0]["lines"])


def get_extractor(platform: str):
    if platform == "github":
        return GitHubExtractor()
    if platform in ("gitlab", "gitlab_self"):
        return GitLabExtractor()
    raise ValueError(f"Unsupported platform: {platform}")
