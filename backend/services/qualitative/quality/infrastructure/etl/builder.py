"""Build a persisted, cleaned qualitative dataset from the collected JSON.

Consumes the platform-agnostic review dicts from the extractors, computes
cleaning flags (is_human) + traces (got_reply, code_changed_after, is_resolved),
persists Review/Thread/Comment/Reaction/Participant rows, and returns summary
stats for the dashboard.
"""
from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import datetime

from django.db import transaction

from quality.models import Review, Thread, Comment, Reaction, Participant
from quality.infrastructure.etl.extractors import get_extractor

logger = logging.getLogger(__name__)


def _parse_dt(value):
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _is_human(comment: dict) -> bool:
    return (
        not comment.get("is_system")
        and not comment.get("author_is_bot")
        and bool((comment.get("body") or "").strip())
    )


@transaction.atomic
def build_dataset(dataset, data: dict) -> dict:
    """(Re)build all rows for *dataset* from *data*; return computed stats."""
    extractor = get_extractor(dataset.platform)
    reviews = extractor.iter_reviews(data)

    # Idempotent rebuild: wipe previous rows (cascades threads/comments/reactions).
    dataset.reviews.all().delete()
    dataset.participants.all().delete()

    participant_counts: Counter = Counter()
    participant_is_bot: dict = {}
    category_counts: Counter = Counter()
    role_counts: Counter = Counter()
    over_time: Counter = Counter()
    reviewer_counts: Counter = Counter()
    resolved = unresolved = threads_with_replies = reactions_count = 0
    comments_total = comments_human = comments_non_human = 0
    threads_count = 0

    for rv in reviews:
        review = Review.objects.create(
            dataset=dataset,
            number=rv["number"] or 0,
            title=rv["title"],
            body=rv["body"],
            author=rv["author"],
            reviewers=rv["reviewers"],
            state=rv["state"],
            url=rv["url"],
            additions=rv["additions"],
            deletions=rv["deletions"],
            changed_files=rv["changed_files"],
            created_at=_parse_dt(rv["created_at"]),
            merged_at=_parse_dt(rv["merged_at"]),
            closed_at=_parse_dt(rv["closed_at"]),
        )

        commit_changes = [
            (_parse_dt(d), set(files)) for d, files in rv.get("commit_changes", [])
        ]
        commit_changes = [(d, f) for d, f in commit_changes if d is not None]

        for th in rv["threads"]:
            thread = Thread.objects.create(
                dataset=dataset,
                review=review,
                external_id=th["external_id"],
                thread_type=th["thread_type"],
                path=th["path"],
                is_resolved=th["is_resolved"],
                is_outdated=th["is_outdated"],
                resolved_by=th["resolved_by"],
            )
            threads_count += 1
            if th["thread_type"] == "inline" and th["is_resolved"] is not None:
                if th["is_resolved"]:
                    resolved += 1
                else:
                    unresolved += 1

            built_comments = [dict(c, _human=_is_human(c)) for c in th["comments"]]
            human_in_thread = sum(1 for c in built_comments if c["_human"])
            if human_in_thread > 1:
                threads_with_replies += 1

            for idx, c in enumerate(built_comments):
                comments_total += 1
                is_human = c["_human"]
                created_dt = _parse_dt(c["created_at"])
                # Reviewer = anyone other than the PR/MR author.
                author_role = (
                    "author" if c["author"] and c["author"] == review.author else "reviewer"
                )

                got_reply = any(
                    built_comments[j]["_human"] for j in range(idx + 1, len(built_comments))
                )
                code_changed_after = _code_changed_after(
                    c.get("path"), created_dt, commit_changes, th.get("is_outdated")
                )

                comment = Comment.objects.create(
                    dataset=dataset,
                    review=review,
                    thread=thread,
                    external_id=c["external_id"],
                    comment_type=th["thread_type"],
                    author=c["author"],
                    author_role=author_role,
                    author_is_bot=bool(c["author_is_bot"]),
                    is_system=bool(c["is_system"]),
                    is_human=is_human,
                    body=c["body"],
                    path=c.get("path") or "",
                    line=c.get("line"),
                    side=c.get("side") or "",
                    diff_hunk=c.get("diff_hunk") or "",
                    reply_to_id=c.get("reply_to_id") or "",
                    created_at=created_dt,
                    updated_at=_parse_dt(c.get("updated_at")),
                    review_number=review.number,
                    is_resolved=th["is_resolved"],
                    got_reply=got_reply,
                    code_changed_after=code_changed_after,
                )

                reactions = c.get("reactions") or []
                if reactions:
                    Reaction.objects.bulk_create([
                        Reaction(comment=comment, content=rx["content"], user=rx.get("user", ""))
                        for rx in reactions
                    ])

                if is_human:
                    comments_human += 1
                    category_counts[th["thread_type"]] += 1
                    role_counts[author_role] += 1
                    reactions_count += len(reactions)
                    if c["author"]:
                        participant_counts[c["author"]] += 1
                        participant_is_bot.setdefault(c["author"], False)
                        if author_role == "reviewer":
                            reviewer_counts[c["author"]] += 1
                    if created_dt:
                        over_time[created_dt.strftime("%Y-%m")] += 1
                else:
                    comments_non_human += 1
                    if c["author"]:
                        participant_is_bot[c["author"]] = (
                            participant_is_bot.get(c["author"], False) or bool(c["author_is_bot"])
                        )

    # Participants
    all_logins = set(participant_counts) | set(participant_is_bot)
    Participant.objects.bulk_create([
        Participant(
            dataset=dataset,
            login=login,
            is_bot=participant_is_bot.get(login, False),
            comment_count=participant_counts.get(login, 0),
        )
        for login in all_logins
    ])

    stats = {
        "platform": dataset.platform,
        "repository_full_name": dataset.repository_full_name,
        "reviews_count": len(reviews),
        "threads_count": threads_count,
        "participants_count": len(all_logins),
        "comments_total": comments_total,
        "comments_human": comments_human,
        "comments_non_human": comments_non_human,
        "by_category": dict(category_counts),
        "by_role": {"reviewer": role_counts.get("reviewer", 0), "author": role_counts.get("author", 0)},
        "resolved_threads": resolved,
        "unresolved_threads": unresolved,
        "threads_with_replies": threads_with_replies,
        "reactions_count": reactions_count,
        "top_authors": [
            {"login": l, "count": n} for l, n in participant_counts.most_common(10)
        ],
        "top_reviewers": [
            {"login": l, "count": n} for l, n in reviewer_counts.most_common(10)
        ],  # reviewers ranked by number of review comments produced
        "comments_over_time": [
            {"month": m, "count": over_time[m]} for m in sorted(over_time)
        ],
    }
    return stats


def _code_changed_after(path, created_dt, commit_changes, is_outdated) -> bool | None:
    """Bosu-style proxy: did code change after the comment was made?"""
    if is_outdated is True:
        return True
    if not path or created_dt is None or not commit_changes:
        return None if is_outdated is None else bool(is_outdated)
    for commit_dt, files in commit_changes:
        if commit_dt > created_dt and path in files:
            return True
    return False
