import csv
import io
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Set
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# DATA EXTRACTION LAYER - Low-level functions to extract data from JSON
# =============================================================================


class DataExtractor:
    """
    Low-level data extraction functions.
    These functions ONLY extract raw data from the JSON structure without any calculations.
    They handle the differences between GitHub and GitLab JSON formats.
    """

    @staticmethod
    def parse_iso_date(date_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO 8601 date string to datetime object"""
        if not date_str:
            return None
        try:
            # Handle both 'Z' suffix and '+00:00' timezone formats
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def format_date(date_str: Optional[str]) -> str:
        """Format ISO date to readable string"""
        if not date_str:
            return ""
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return date_str

    def get_first_review_date(self, item: dict) -> Optional[str]:
        """
        Return ISO date string of the first human review comment.
        This is the boundary between initial_size and rework.
        Subclasses must implement this.
        """
        raise NotImplementedError

    def count_human_comments(self, item: dict) -> int:
        """
        Count all human-written comments (excluding system/bot notes).
        Subclasses must implement this.
        """
        raise NotImplementedError


class GitHubDataExtractor(DataExtractor):
    """Extract data from GitHub Pull Request JSON format"""

    @staticmethod
    def get_item_key() -> str:
        return "pull_requests"

    @staticmethod
    def get_item_id(details: dict) -> Optional[int]:
        """Get PR number"""
        return details.get("number")

    @staticmethod
    def get_title(details: dict) -> str:
        return details.get("title", "")

    @staticmethod
    def get_author(details: dict) -> str:
        """Get PR author login"""
        return details.get("user", {}).get("login", "")

    @staticmethod
    def get_state(details: dict) -> str:
        """Get PR state (open, closed, merged)"""
        if details.get("merged"):
            return "merged"
        return details.get("state", "")

    @staticmethod
    def get_created_at(details: dict) -> Optional[str]:
        return details.get("created_at")

    @staticmethod
    def get_merged_at(details: dict) -> Optional[str]:
        return details.get("merged_at")

    @staticmethod
    def get_closed_at(details: dict) -> Optional[str]:
        return details.get("closed_at")

    @staticmethod
    def get_merged_by(details: dict) -> str:
        merged_by = details.get("merged_by")
        return merged_by.get("login", "") if merged_by else ""

    @staticmethod
    def get_commits(item: dict) -> List[dict]:
        """Get list of commits from PR"""
        return item.get("commits", [])

    @staticmethod
    def get_commit_sha(commit: dict) -> str:
        """Get commit SHA"""
        return commit.get("commit_sha", "") or commit.get("sha", "")

    @staticmethod
    def get_commit_author_name(commit: dict) -> str:
        """Extract commit author name from GitHub commit structure"""
        # Structure: commit.details.commit.author.name
        details = commit.get("details", {})
        return details.get("commit", {}).get("author", {}).get("name", "")

    @staticmethod
    def get_commit_author_login(commit: dict) -> str:
        """Extract commit author login from GitHub commit structure"""
        # Structure: commit.details.author.login
        details = commit.get("details", {})
        return details.get("author", {}).get("login", "")

    @staticmethod
    def get_commit_date(commit: dict) -> Optional[str]:
        """Extract commit date from GitHub commit structure"""
        # Structure: commit.details.commit.author.date
        details = commit.get("details", {})
        return details.get("commit", {}).get("author", {}).get("date")

    @staticmethod
    def get_commit_message(commit: dict) -> str:
        """Extract commit message from GitHub commit structure"""
        details = commit.get("details", {})
        return details.get("commit", {}).get("message", "")

    @staticmethod
    def get_commit_additions(commit: dict) -> int:
        """Get additions from commit changes"""
        changes = commit.get("changes", [])
        return sum(c.get("additions", 0) or 0 for c in changes)

    @staticmethod
    def get_commit_deletions(commit: dict) -> int:
        """Get deletions from commit changes"""
        changes = commit.get("changes", [])
        return sum(c.get("deletions", 0) or 0 for c in changes)

    @staticmethod
    def get_files(item: dict) -> List[dict]:
        """Get list of modified files"""
        return item.get("files", [])

    @staticmethod
    def get_file_name(file: dict) -> str:
        return file.get("filename", "")

    @staticmethod
    def get_file_additions(file: dict) -> int:
        return file.get("additions", 0) or 0

    @staticmethod
    def get_file_deletions(file: dict) -> int:
        return file.get("deletions", 0) or 0

    @staticmethod
    def get_pr_additions(details: dict) -> int:
        """Get total additions from PR details"""
        return details.get("additions", 0) or 0

    @staticmethod
    def get_pr_deletions(details: dict) -> int:
        """Get total deletions from PR details"""
        return details.get("deletions", 0) or 0

    @staticmethod
    def get_comments(item: dict) -> List[dict]:
        """Get issue comments"""
        return item.get("comments", [])

    @staticmethod
    def get_reviews(item: dict) -> List[dict]:
        """Get PR reviews"""
        return item.get("reviews", [])

    @staticmethod
    def get_review_comments(item: dict) -> List[dict]:
        """Get review comments (inline code comments)"""
        return item.get("review_comments", [])

    @staticmethod
    def get_comment_author(comment: dict) -> str:
        return comment.get("user", {}).get("login", "")

    @staticmethod
    def get_review_author(review: dict) -> str:
        return review.get("user", {}).get("login", "")

    @staticmethod
    def get_unique_reviewers(item: dict) -> Set[str]:
        """Get set of unique reviewers"""
        reviewers = set()
        for review in item.get("reviews", []):
            user = review.get("user", {}).get("login")
            if user:
                reviewers.add(user)
        return reviewers

    @staticmethod
    def get_unique_discussioners(item: dict) -> Set[str]:
        """Get set of unique users who participated in discussions"""
        discussioners = set()

        for comment in item.get("comments", []):
            user = comment.get("user", {}).get("login")
            if user:
                discussioners.add(user)

        for review in item.get("reviews", []):
            user = review.get("user", {}).get("login")
            if user:
                discussioners.add(user)

        for rc in item.get("review_comments", []):
            user = rc.get("user", {}).get("login")
            if user:
                discussioners.add(user)

        return discussioners

    @staticmethod
    def get_first_review_date(item: dict) -> Optional[str]:
        """
        Return the ISO date string of the first review or comment on the PR.
        Uses submitted_at for reviews and created_at for comments.
        Returns None if no review activity found.
        """
        dates = []
        for review in item.get('reviews', []):
            dt = review.get('submitted_at')
            if dt:
                dates.append(dt)
        for comment in item.get('comments', []):
            dt = comment.get('created_at')
            if dt:
                dates.append(dt)
        for rc in item.get('review_comments', []):
            dt = rc.get('created_at')
            if dt:
                dates.append(dt)
        return min(dates) if dates else None

    @staticmethod
    def count_human_comments(item: dict) -> int:
        """Count all human comments: issue comments + review comments."""
        return len(item.get('comments', [])) + len(item.get('review_comments', []))


class GitLabDataExtractor(DataExtractor):
    """Extract data from GitLab Merge Request JSON format"""

    @staticmethod
    def get_item_key() -> str:
        return "merge_requests"

    @staticmethod
    def get_item_id(details: dict) -> Optional[int]:
        """Get MR IID"""
        return details.get("iid")

    @staticmethod
    def get_title(details: dict) -> str:
        return details.get("title", "")

    @staticmethod
    def get_author(details: dict) -> str:
        """Get MR author username"""
        return details.get("author", {}).get("username", "")

    @staticmethod
    def get_state(details: dict) -> str:
        """Get MR state"""
        return details.get("state", "")

    @staticmethod
    def get_created_at(details: dict) -> Optional[str]:
        return details.get("created_at")

    @staticmethod
    def get_merged_at(details: dict) -> Optional[str]:
        return details.get("merged_at")

    @staticmethod
    def get_closed_at(details: dict) -> Optional[str]:
        return details.get("closed_at")

    @staticmethod
    def get_merged_by(details: dict) -> str:
        merged_by = details.get("merged_by")
        return merged_by.get("username", "") if merged_by else ""

    @staticmethod
    def get_commits(item: dict) -> List[dict]:
        """Get list of commits from MR"""
        return item.get("commits", [])

    @staticmethod
    def get_commit_sha(commit: dict) -> str:
        """Get commit SHA"""
        return commit.get("commit_id", "") or commit.get("id", "")

    @staticmethod
    def get_commit_author_name(commit: dict) -> str:
        """Extract commit author name from GitLab commit structure"""
        # Structure: commit.details.author_name
        details = commit.get("details", {})
        return details.get("author_name", "")

    @staticmethod
    def get_commit_author_login(commit: dict) -> str:
        """GitLab doesn't have login in commits, return author_name"""
        details = commit.get("details", {})
        return details.get("author_name", "")

    @staticmethod
    def get_commit_date(commit: dict) -> Optional[str]:
        """Extract commit date from GitLab commit structure"""
        # Structure: commit.details.authored_date or commit.details.created_at
        details = commit.get("details", {})
        return details.get("authored_date") or details.get("created_at")

    @staticmethod
    def get_commit_message(commit: dict) -> str:
        """Extract commit message from GitLab commit structure"""
        details = commit.get("details", {})
        return details.get("message", "") or details.get("title", "")

    @staticmethod
    def get_commit_additions(commit: dict) -> int:
        """
        Get additions from commit changesHist by parsing the diff.

        GitLab stores diffs in unified format. Lines starting with '+'
        (but not '+++') are additions.
        """
        total_additions = 0
        for change in commit.get("changesHist", []):
            diff = change.get("diff", "")
            for line in diff.split("\n"):
                # Count lines that start with '+' but not '+++' (file header)
                if line.startswith("+") and not line.startswith("+++"):
                    total_additions += 1
        return total_additions

    @staticmethod
    def get_commit_deletions(commit: dict) -> int:
        """
        Get deletions from commit changesHist by parsing the diff.

        Lines starting with '-' (but not '---') are deletions.
        """
        total_deletions = 0
        for change in commit.get("changesHist", []):
            diff = change.get("diff", "")
            for line in diff.split("\n"):
                # Count lines that start with '-' but not '---' (file header)
                if line.startswith("-") and not line.startswith("---"):
                    total_deletions += 1
        return total_deletions

    @staticmethod
    def get_files(item: dict) -> List[dict]:
        """Get list of modified files from changes"""
        changes = item.get("changes", {})
        if isinstance(changes, dict):
            return changes.get("changes", []) or changes.get("diffs", [])
        return []

    @staticmethod
    def get_file_name(file: dict) -> str:
        return file.get("new_path", "") or file.get("old_path", "")

    @staticmethod
    def get_file_additions(file: dict) -> int:
        """Parse additions from file diff"""
        diff = file.get("diff", "")
        additions = 0
        for line in diff.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                additions += 1
        return additions

    @staticmethod
    def get_file_deletions(file: dict) -> int:
        """Parse deletions from file diff"""
        diff = file.get("diff", "")
        deletions = 0
        for line in diff.split("\n"):
            if line.startswith("-") and not line.startswith("---"):
                deletions += 1
        return deletions

    @staticmethod
    def get_mr_additions(details: dict) -> int:
        """Get total additions - GitLab stores this differently"""
        # GitLab may not have direct additions count
        return 0

    @staticmethod
    def get_mr_deletions(details: dict) -> int:
        """Get total deletions"""
        return 0

    @staticmethod
    def get_discussions(item: dict) -> List[dict]:
        """Get discussions"""
        return item.get("discussions", [])

    @staticmethod
    def get_notes(item: dict) -> List[dict]:
        """Get notes (comments)"""
        return item.get("notes", [])

    @staticmethod
    def get_note_author(note: dict) -> str:
        return note.get("author", {}).get("username", "")

    @staticmethod
    def get_unique_reviewers(item: dict) -> Set[str]:
        """
        Get set of unique reviewers from details.reviewers[].
        GitLab stores assigned reviewers explicitly in the MR details.
        """
        reviewers = set()
        details = item.get('details', {})
        for r in details.get('reviewers', []):
            username = r.get('username') if isinstance(r, dict) else None
            if username:
                reviewers.add(username)
        return reviewers

    @staticmethod
    def _is_system_note(note: dict) -> bool:
        """
        Check if a note is a system note.
        GitLab stores the 'system' field as either a Python bool or the
        string 'True'/'False' depending on how the JSON was serialised.
        """
        val = note.get('system', False)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.strip().lower() in ('true', '1')
        return bool(val)

    @staticmethod
    def get_unique_discussioners(item: dict) -> Set[str]:
        """
        Get set of unique users who posted human (non-system) notes.
        System notes (e.g. 'added 3 commits', 'requested review from @x')
        are excluded.
        """
        discussioners = set()

        for discussion in item.get('discussions', []):
            for note in discussion.get('notes', []):
                if GitLabDataExtractor._is_system_note(note):
                    continue
                author = note.get('author', {}).get('username')
                if author:
                    discussioners.add(author)

        for note in item.get('notes', []):
            if GitLabDataExtractor._is_system_note(note):
                continue
            author = note.get('author', {}).get('username')
            if author:
                discussioners.add(author)

        return discussioners

    @staticmethod
    def get_first_review_date(item: dict) -> Optional[str]:
        """
        Return the ISO date string of the first human (non-system) comment
        in any discussion or note. Returns None if no human comment exists.
        This is the boundary between initial_size and rework.
        """
        dates = []
        for discussion in item.get('discussions', []):
            for note in discussion.get('notes', []):
                if GitLabDataExtractor._is_system_note(note):
                    continue
                created_at = note.get('created_at')
                if created_at:
                    dates.append(created_at)
        for note in item.get('notes', []):
            if GitLabDataExtractor._is_system_note(note):
                continue
            created_at = note.get('created_at')
            if created_at:
                dates.append(created_at)
        return min(dates) if dates else None

    @staticmethod
    def count_human_comments(item: dict) -> int:
        """Count all non-system notes (human-written comments)."""
        count = 0
        seen_ids = set()
        for discussion in item.get('discussions', []):
            for note in discussion.get('notes', []):
                if GitLabDataExtractor._is_system_note(note):
                    continue
                nid = note.get('id')
                if nid not in seen_ids:
                    seen_ids.add(nid)
                    count += 1
        for note in item.get('notes', []):
            if GitLabDataExtractor._is_system_note(note):
                continue
            nid = note.get('id')
            if nid not in seen_ids:
                seen_ids.add(nid)
                count += 1
        return count


def get_data_extractor(platform: str):
    """Factory function to get the appropriate data extractor"""
    extractors = {
        "github": GitHubDataExtractor,
        "gitlab": GitLabDataExtractor,
    }
    extractor_class = extractors.get(platform.lower())
    if not extractor_class:
        raise ValueError(f"Unsupported platform: {platform}")
    return extractor_class()


# =============================================================================
# METRICS CALCULATION LAYER - Pure calculation functions
# =============================================================================


class MetricsCalculator:
    """
    Pure calculation functions for code review metrics.
    These functions take already-extracted data and compute metrics.
    They are platform-agnostic and work with normalized data.

    Metrics Reference:
    - Lead Time: Time from PR/MR creation to close/merge (in minutes)
    - Churn: Total lines added and deleted across commits
    - Entropy: Shannon entropy measuring distribution of changes across files
    - Mean Time Between Commits: Average time interval between consecutive commits
    - Author Contributions: Count of major (>=5% commits) vs minor (<5%) contributors
    - Delta Time: Days since Unix epoch (for time-series analysis)
    - Rework Size: Estimated lines changed after code review feedback
    """

    @staticmethod
    def calculate_lead_time(
        created_at: Optional[datetime], closed_at: Optional[datetime]
    ) -> float:
        """
        Calculate lead time in MINUTES.

        Lead Time = (closed_at - created_at) in minutes.

        Args:
            created_at: When the PR/MR was created
            closed_at: When the PR/MR was closed/merged

        Returns:
            Lead time in minutes, or 0 if dates are invalid
        """
        if not created_at or not closed_at:
            return 0.0
        delta = closed_at - created_at
        return round(delta.total_seconds() / 60, 2)

    @staticmethod
    def calculate_mean_time_between_commits(commit_dates: List[datetime]) -> float:
        """
        Calculate mean time between consecutive commits in seconds.

        Formula: sum(time_diffs) / count(time_diffs)
        where time_diffs[i] = dates[i+1] - dates[i]

        Args:
            commit_dates: List of parsed datetime objects for each commit

        Returns:
            Mean time between commits in seconds, or 0 if < 2 commits
        """
        if len(commit_dates) < 2:
            return 0.0

        sorted_dates = sorted(commit_dates)
        time_diffs = [
            (sorted_dates[i + 1] - sorted_dates[i]).total_seconds()
            for i in range(len(sorted_dates) - 1)
        ]

        if not time_diffs:
            return 0.0

        return round(sum(time_diffs) / len(time_diffs), 2)

    @staticmethod
    def calculate_churn(
        commit_additions: List[int], commit_deletions: List[int]
    ) -> Tuple[float, float]:
        """
        Calculate code churn (total additions and deletions across all commits).

        Churn represents the total volume of code changes.

        Args:
            commit_additions: List of additions per commit
            commit_deletions: List of deletions per commit

        Returns:
            Tuple of (total_additions, total_deletions)
        """
        total_additions = sum(a for a in commit_additions if a)
        total_deletions = sum(d for d in commit_deletions if d)
        return float(total_additions), float(total_deletions)

    @staticmethod
    def calculate_entropy(file_changes: List[int]) -> float:
        """
        Calculate Shannon entropy based on file modification distribution.

        Entropy measures how evenly changes are distributed across files.
        - Low entropy: changes concentrated in few files
        - High entropy: changes spread across many files

        Formula: -Σ(p_i * log2(p_i))
        where p_i = changes_in_file_i / total_changes

        Args:
            file_changes: List of (additions + deletions) per file

        Returns:
            Shannon entropy value (0 to log2(n) where n = number of files)
        """
        if not file_changes:
            return 0.0

        # Filter out zero changes
        changes = [c for c in file_changes if c > 0]
        if not changes:
            return 0.0

        total = sum(changes)
        if total == 0:
            return 0.0

        entropy = 0.0
        for c in changes:
            p = c / total
            if p > 0:
                entropy -= p * math.log2(p)

        return round(entropy, 6)

    @staticmethod
    def calculate_author_contributions(
        author_commit_counts: Dict[str, int],
    ) -> Tuple[int, int]:
        """
        Calculate minor and major author counts.
        
        - Major author: contributed > 5% of commits
        - Minor author: contributed <= 5% of commits
        
        Args:
            author_commit_counts: Dict mapping author name to commit count

        Returns:
            Tuple of (nb_minor, nb_major)
        """
        if not author_commit_counts:
            return 0, 0

        total_commits = sum(author_commit_counts.values())
        if total_commits == 0:
            return 0, 0

        nb_minor = 0
        nb_major = 0

        for author, count in author_commit_counts.items():
            contribution_pct = count / total_commits
            if contribution_pct > 0.05:
                nb_major += 1
            else:
                nb_minor += 1

        return nb_minor, nb_major

    @staticmethod
    def calculate_delta_time(created_at: Optional[datetime], project_created_at: Optional[datetime] = None) -> float:
        """
        Calculate delta time as the number of days between the project creation
        and the MR/PR creation.
        
        Args:
            created_at: When the PR/MR was created
            project_created_at: When the project/repository was created on the platform
            
        Returns:
            Fractional days between project creation and PR/MR creation.
            Falls back to days since Unix epoch if project_created_at is not available.
        """
        if not created_at:
            return 0.0

        # Ensure timezone awareness
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        
        if project_created_at:
            if project_created_at.tzinfo is None:
                project_created_at = project_created_at.replace(tzinfo=timezone.utc)
            delta = created_at - project_created_at
        else:
            epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
            delta = created_at - epoch
        
        return round(delta.total_seconds() / 86400, 6)

    @staticmethod
    def calculate_rework_size(commits: List[dict], first_review_date: Optional[datetime],
                              extractor) -> float:
        """
        Calculate rework size: total lines changed in commits authored
        AFTER the first human review comment.

        Definition (agreed):
          - rework = work done in response to reviewer feedback
          - boundary = date of the first non-system human comment/review

        If no review comment exists → rework = 0 (the MR had no review).

        Args:
            commits: List of commit dicts
            first_review_date: Parsed datetime of first human review comment.
                               None means no review → rework = 0.
            extractor: Platform-specific DataExtractor for reading commit data

        Returns:
            Total added + deleted lines in commits after first_review_date.
        """
        if not first_review_date or not commits:
            return 0.0

        rework = 0
        for commit in commits:
            commit_date_str = extractor.get_commit_date(commit)
            commit_date = DataExtractor.parse_iso_date(commit_date_str)
            if commit_date and commit_date > first_review_date:
                rework += extractor.get_commit_additions(commit)
                rework += extractor.get_commit_deletions(commit)
        return float(rework)


class CSVGenerator:
    """Generate structured CSV from collected data with filters"""

    def __init__(self, platform: str):
        self.platform = platform
        self.item_key = "pull_requests" if platform == "github" else "merge_requests"

    def _get_item_files(self, item: dict) -> list:
        """Extract the list of modified files from an item, handling both platforms."""
        if self.platform == 'github':
            return item.get('files', [])
        changes = item.get('changes', {})
        if isinstance(changes, dict):
            return changes.get('changes', []) or changes.get('diffs', [])
        return []

    def apply_filters(self, raw_data: dict, filters: dict) -> dict:
        """Apply filters to raw data"""
        items = raw_data.get(self.item_key, [])
        filtered_items = []

        for item in items:
            # Filter by file extensions
            if filters.get("file_extensions"):
                files = self._get_item_files(item)
                has_extension = False

                for file in files:
                    filename = file.get("filename") or file.get("new_path")
                    if filename:
                        for ext in filters["file_extensions"]:
                            if filename.endswith(ext):
                                has_extension = True
                                break

                if not has_extension:
                    continue

            # Filter by authors
            if filters.get("authors"):
                author = item.get("details", {}).get("user", {}).get(
                    "login"
                ) or item.get("details", {}).get("author", {}).get("username")

                if author not in filters["authors"]:
                    continue

            # Filter by keyword_filters (new format: array of {field, keywords})
            keyword_filters = filters.get("keyword_filters", [])
            if keyword_filters:
                passes_all_keyword_filters = True

                for kf in keyword_filters:
                    keyword_field = kf.get("field")
                    keywords = kf.get("keywords", [])

                    if not keyword_field or not keywords:
                        continue

                    text_to_search = self._get_text_for_keyword_field(
                        item, keyword_field
                    )
                    has_keyword = any(
                        keyword.lower() in text_to_search for keyword in keywords
                    )

                    if not has_keyword:
                        passes_all_keyword_filters = False
                        break

                if not passes_all_keyword_filters:
                    continue

            # Legacy support: Filter by keywords (old format: single keyword_field + keywords)
            elif filters.get("keywords") and filters.get("keyword_field"):
                keyword_field = filters["keyword_field"]
                keywords = filters["keywords"]

                text_to_search = self._get_text_for_keyword_field(item, keyword_field)
                has_keyword = any(
                    keyword.lower() in text_to_search for keyword in keywords
                )

                if not has_keyword:
                    continue

            filtered_items.append(item)
        
        result = {self.item_key: filtered_items}
        # Preserve top-level metadata (e.g. project_created_at)
        for key, value in raw_data.items():
            if key != self.item_key:
                result[key] = value
        return result
    
    def _get_text_for_keyword_field(self, item: dict, keyword_field: str) -> str:
        """Extract text to search based on keyword field"""
        if keyword_field == "title":
            return item.get("details", {}).get("title", "").lower()
        elif keyword_field == "description":
            return item.get("details", {}).get("body", "").lower()
        elif keyword_field == "comments":
            comments = item.get("comments", []) + item.get("notes", [])
            return " ".join([c.get("body", "").lower() for c in comments])
        elif keyword_field == "commit_message":
            commits = item.get("commits", [])
            commit_messages = []
            for commit in commits:
                # GitHub format - nested under details.commit.message
                if "details" in commit:
                    details = commit.get("details", {})
                    if "commit" in details and "message" in details.get("commit", {}):
                        commit_messages.append(details["commit"]["message"].lower())
                    elif "message" in details:
                        commit_messages.append(details["message"].lower())
                # Alternative GitHub format - directly under commit.message
                elif "commit" in commit and "message" in commit.get("commit", {}):
                    commit_messages.append(commit["commit"]["message"].lower())
                # GitLab format - message directly in commit
                elif "message" in commit:
                    commit_messages.append(commit["message"].lower())
                elif "title" in commit:
                    commit_messages.append(commit["title"].lower())
            return " ".join(commit_messages)
        return ""

    def generate_csv(self, data: dict) -> str:
        """Generate CSV content from filtered data"""
        items = data.get(self.item_key, [])

        output = io.StringIO()

        if self.platform == "github":
            headers = [
                "PR_Number",
                "Title",
                "Author",
                "Status",
                "State",
                "Creation_Date",
                "Merge_Date",
                "Close_Date",
                "Merged_By",
                "Commits_Count",
                "Comments_Count",
                "Reviews_Count",
                "Review_Comments_Count",
                "Files_Changed",
                "Additions",
                "Deletions",
            ]
        else:
            headers = [
                "MR_IID",
                "Title",
                "Author",
                "Status",
                "State",
                "Creation_Date",
                "Merge_Date",
                "Close_Date",
                "Merged_By",
                "Commits_Count",
                "Notes_Count",
                "Discussions_Count",
                "Files_Changed",
                "Additions",
                "Deletions",
            ]

        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()

        for item in items:
            details = item.get("details", {})

            if self.platform == "github":
                row = {
                    "PR_Number": details.get("number"),
                    "Title": details.get("title", ""),
                    "Author": details.get("user", {}).get("login", ""),
                    "Status": details.get("state", ""),
                    "State": (
                        "merged" if details.get("merged") else details.get("state")
                    ),
                    "Creation_Date": self._format_date(details.get("created_at")),
                    "Merge_Date": self._format_date(details.get("merged_at")),
                    "Close_Date": self._format_date(details.get("closed_at")),
                    "Merged_By": (
                        details.get("merged_by", {}).get("login", "")
                        if details.get("merged_by")
                        else ""
                    ),
                    "Commits_Count": len(item.get("commits", [])),
                    "Comments_Count": len(item.get("comments", [])),
                    "Reviews_Count": len(item.get("reviews", [])),
                    "Review_Comments_Count": len(item.get("review_comments", [])),
                    "Files_Changed": len(item.get("files", [])),
                    "Additions": details.get("additions", 0),
                    "Deletions": details.get("deletions", 0),
                }
            else:
                row = {
                    'MR_IID': details.get('iid'),
                    'Title': details.get('title', ''),
                    'Author': details.get('author', {}).get('username', ''),
                    'Status': details.get('state', ''),
                    'State': details.get('state', ''),
                    'Creation_Date': self._format_date(details.get('created_at')),
                    'Merge_Date': self._format_date(details.get('merged_at')),
                    'Close_Date': self._format_date(details.get('closed_at')),
                    'Merged_By': details.get('merged_by', {}).get('username', '') if details.get('merged_by') else '',
                    'Commits_Count': len(item.get('commits', [])),
                    'Notes_Count': len(item.get('notes', [])),
                    'Discussions_Count': len(item.get('discussions', [])),
                    'Files_Changed': len(item.get('changes', {}).get('changes', []) or item.get('changes', {}).get('diffs', [])) if item.get('changes') else 0,
                    'Additions': sum(
                        sum(1 for l in f.get('diff','').splitlines() if l.startswith('+') and not l.startswith('+++'))
                        for f in (item.get('changes', {}).get('changes', []) if isinstance(item.get('changes'), dict) else [])
                    ),
                    'Deletions': sum(
                        sum(1 for l in f.get('diff','').splitlines() if l.startswith('-') and not l.startswith('---'))
                        for f in (item.get('changes', {}).get('changes', []) if isinstance(item.get('changes'), dict) else [])
                    )
                }

            writer.writerow(row)

        return output.getvalue()

    def get_preview(self, data: dict, rows: int = 5) -> List[Dict]:
        """Get preview of first N rows"""
        items = data.get(self.item_key, [])[:rows]
        preview = []

        for item in items:
            details = item.get("details", {})

            if self.platform == "github":
                preview.append(
                    {
                        "PR_Number": details.get("number"),
                        "Title": details.get("title", ""),
                        "Author": details.get("user", {}).get("login", ""),
                        "Status": details.get("state", ""),
                        "Creation_Date": self._format_date(details.get("created_at")),
                        "Comments": len(item.get("comments", [])),
                    }
                )
            else:
                preview.append(
                    {
                        "MR_IID": details.get("iid"),
                        "Title": details.get("title", ""),
                        "Author": details.get("author", {}).get("username", ""),
                        "Status": details.get("state", ""),
                        "Creation_Date": self._format_date(details.get("created_at")),
                        "Notes": len(item.get("notes", [])),
                    }
                )

        return preview

    def _format_date(self, date_str: str) -> str:
        """Format ISO date to readable format"""
        if not date_str:
            return ""
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return date_str


class PlatformAdapter:
    """
    Abstract adapter for platform-specific data extraction.
    Provides a unified interface to access PR/MR data regardless of chosen platform.
    """

    def __init__(self, platform: str):
        self.platform = platform

    def get_item_key(self) -> str:
        """Get the key for items in raw data (pull_requests or merge_requests)"""
        raise NotImplementedError

    def get_item_id(self, details: dict):
        """Get the unique identifier of the PR/MR"""
        raise NotImplementedError

    def get_author(self, details: dict) -> str:
        """Get the author username"""
        raise NotImplementedError

    def get_merged_by(self, details: dict) -> str:
        """Get the username of who merged the item"""
        raise NotImplementedError

    def get_discussions_count(self, item: dict) -> int:
        """Get the number of discussions/comments"""
        raise NotImplementedError

    def get_reviewers(self, item: dict) -> set:
        """Get unique reviewers"""
        raise NotImplementedError

    def get_discussioners(self, item: dict) -> set:
        """Get unique users who participated in discussions"""
        raise NotImplementedError

    def get_files(self, item: dict) -> list:
        """Get list of modified files"""
        raise NotImplementedError

    def get_additions(self, details: dict) -> int:
        """Get total additions"""
        raise NotImplementedError

    def get_deletions(self, details: dict) -> int:
        """Get total deletions"""
        raise NotImplementedError

    def get_commit_author(self, commit: dict) -> str:
        """Get commit author name"""
        raise NotImplementedError

    def get_commit_date(self, commit: dict) -> str:
        """Get commit date string"""
        raise NotImplementedError


class GitHubAdapter(PlatformAdapter):
    """Adapter for GitHub Pull Requests"""

    def __init__(self):
        super().__init__("github")

    def get_item_key(self) -> str:
        return "pull_requests"

    def get_item_id(self, details: dict):
        return details.get("number")

    def get_author(self, details: dict) -> str:
        return details.get("user", {}).get("login", "")

    def get_merged_by(self, details: dict) -> str:
        merged_by = details.get("merged_by")
        return merged_by.get("login", "") if merged_by else ""

    def get_discussions_count(self, item: dict) -> int:
        # GitHub: count comments
        return len(item.get("comments", []))

    def get_reviewers(self, item: dict) -> set:
        reviewers = set()
        for review in item.get("reviews", []):
            user = review.get("user", {}).get("login")
            if user:
                reviewers.add(user)
        return reviewers

    def get_discussioners(self, item: dict) -> set:
        discussioners = set()

        # From comments
        for comment in item.get("comments", []):
            user = comment.get("user", {}).get("login")
            if user:
                discussioners.add(user)

        # From reviews
        for review in item.get("reviews", []):
            user = review.get("user", {}).get("login")
            if user:
                discussioners.add(user)

        # From review comments
        for rc in item.get("review_comments", []):
            user = rc.get("user", {}).get("login")
            if user:
                discussioners.add(user)

        return discussioners

    def get_files(self, item: dict) -> list:
        return item.get("files", [])

    def get_additions(self, details: dict) -> int:
        return details.get("additions", 0) or 0

    def get_deletions(self, details: dict) -> int:
        return details.get("deletions", 0) or 0

    def get_commit_author(self, commit: dict) -> str:
        return (
            commit.get("details", {})
            .get("commit", {})
            .get("author", {})
            .get("name", "")
        )

    def get_commit_date(self, commit: dict) -> str:
        return (
            commit.get("details", {})
            .get("commit", {})
            .get("author", {})
            .get("date", "")
        )


class GitLabAdapter(PlatformAdapter):
    """Adapter for GitLab Merge Requests"""

    def __init__(self):
        super().__init__("gitlab")

    def get_item_key(self) -> str:
        return "merge_requests"

    def get_item_id(self, details: dict):
        return details.get("iid")

    def get_author(self, details: dict) -> str:
        return details.get("author", {}).get("username", "")

    def get_merged_by(self, details: dict) -> str:
        merged_by = details.get("merged_by")
        return merged_by.get("username", "") if merged_by else ""

    def get_discussions_count(self, item: dict) -> int:
        # GitLab: count discussions
        return len(item.get("discussions", []))

    def get_reviewers(self, item: dict) -> set:
        """
        Return the set of assigned reviewers from details.reviewers[].
        GitLab explicitly tracks assigned reviewers separately from
        discussion participants.
        """
        reviewers = set()
        details = item.get('details', {})
        for r in details.get('reviewers', []):
            username = r.get('username') if isinstance(r, dict) else None
            if username:
                reviewers.add(username)
        return reviewers

    def get_discussioners(self, item: dict) -> set:
        """
        Return unique users who posted human (non-system) notes.
        Handles system field as both bool and string ('True'/'False').
        """
        discussioners = set()

        def is_system(note: dict) -> bool:
            val = note.get('system', False)
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                return val.strip().lower() in ('true', '1')
            return bool(val)

        for discussion in item.get('discussions', []):
            for note in discussion.get('notes', []):
                if is_system(note):
                    continue
                author = note.get('author', {}).get('username')
                if author:
                    discussioners.add(author)

        for note in item.get('notes', []):
            if is_system(note):
                continue
            author = note.get('author', {}).get('username')
            if author:
                discussioners.add(author)

        return discussioners

    def get_files(self, item: dict) -> list:
        changes = item.get("changes", {})
        if isinstance(changes, dict):
            return changes.get("changes", []) or changes.get("diffs", [])
        return []

    def get_additions(self, details: dict) -> int:
        """
        GitLab MR details do not carry line-level additions/deletions.
        changes_count is the number of FILES changed, not lines.
        Actual additions must be summed from file diffs.
        Returns 0 here; callers must use get_file_additions() per file.
        """
        return 0

    def get_deletions(self, details: dict) -> int:
        """
        Same as get_additions: GitLab details only expose file count.
        Callers must sum get_file_deletions() across files.
        """
        return 0
    
    def get_commit_author(self, commit: dict) -> str:
        return commit.get("details", {}).get("author_name", "")

    def get_commit_date(self, commit: dict) -> str:
        return commit.get("details", {}).get("authored_date", "")


def get_platform_adapter(platform: str) -> PlatformAdapter:
    """Factory function to get the appropriate platform adapter"""
    adapters = {
        "github": GitHubAdapter,
        "gitlab": GitLabAdapter,
    }
    adapter_class = adapters.get(platform.lower())
    if not adapter_class:
        raise ValueError(
            f"Unsupported platform: {platform}. Supported: {list(adapters.keys())}"
        )
    return adapter_class()



class StatisticsCSVGenerator:
    """
    Generate project statistics CSV with metrics per PR/MR.

    Uses DataExtractor for platform-specific data access and
    MetricsCalculator for pure metric calculations.
    """

    ALL_FEATURES = [
        "Creation_Date",
        "Lead_Time",
        "#Discussions",
        "#Commits",
        "Mean_Time_between_commits",
        "Commiters",
        "Commiter_Names",
        "#UniqueCommiters",
        "nb_minor_author",
        "nb_major_author",
        "delta_time",
        "churn_addition",
        "churn_deletions",
        "initial_size",
        "hist_entropy",
        "modified_files",
        "filetypes",
        "state",
        "rework_size",
        "Author",
        "Reviewers",
        "#people",
        "#reviewers",
        "#commiters",
        "#discussionners",
        "additions",
        "deletions",
        "comments",
    ]

    def __init__(self, platform: str):
        self.platform = platform
        self.extractor = get_data_extractor(platform)
        self.adapter = get_platform_adapter(platform)
        self.item_key = self.extractor.get_item_key()
        self.item_id_column = "PR_ID" if platform == "github" else "MR_ID"
        self.initial_size_column = (
            "initial_pr_size" if platform == "github" else "initial_mr_size"
        )

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def generate_statistics_csv(
        self,
        data: dict,
        collection_plan,
        selected_features: Optional[List[str]] = None,
    ) -> str:
        """
        Generate statistics CSV with one row per PR/MR.

        Args:
            data: Filtered PR/MR data dict.
            collection_plan: Collection plan with repository info.
            selected_features: Feature IDs to include; None/empty → all features.

        Returns:
            CSV content as a string.
        """
        items = data.get(self.item_key, [])
        project_created_at = DataExtractor.parse_iso_date(
            data.get("project_created_at")
        )

        headers = self._build_headers(selected_features)

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()

        for item in items:
            full_row = self._build_row(item, collection_plan, project_created_at)
            filtered_row = {k: v for k, v in full_row.items() if k in headers}
            writer.writerow(filtered_row)

        return output.getvalue()

    # =========================================================================
    # HEADER HELPERS
    # =========================================================================

    def _build_headers(self, selected_features: Optional[List[str]]) -> List[str]:
        base = ["Project_ID", self.item_id_column]
        feature_to_header = {f: f for f in self.ALL_FEATURES}
        feature_to_header["initial_size"] = self.initial_size_column

        if selected_features:
            feature_headers = [
                feature_to_header[f]
                for f in self.ALL_FEATURES
                if f in selected_features
            ]
        else:
            feature_headers = [feature_to_header[f] for f in self.ALL_FEATURES]

        return base + feature_headers

    # =========================================================================
    # ROW BUILDER
    # =========================================================================

    def _build_row(
        self, item: dict, collection_plan, project_created_at=None
    ) -> dict:
        """Build one CSV row for a single PR/MR item."""
        print(f"Building row for item ID: {self.adapter.get_item_id(item.get('details', {}))}")
        details = item.get("details", {})
        commits = self.extractor.get_commits(item)

        # --- Dates -----------------------------------------------------------
        created_at_str = self.extractor.get_created_at(details)
        closed_at_str = self.extractor.get_closed_at(
            details
        ) or self.extractor.get_merged_at(details)
        created_at = DataExtractor.parse_iso_date(created_at_str)
        closed_at = DataExtractor.parse_iso_date(closed_at_str)

        author = self._extract_author(details)

        # "Commiters" column = set of author names found in each commit's details.
        # "#UniqueCommiters" counts unique logins/usernames for deduplication.
        committer_names, committer_logins, author_counts = self._extract_committers(
            commits
        )

        # --- Files & churn ---------------------------------------------------
        files = self.extractor.get_files(item)
        file_changes = [
            self.extractor.get_file_additions(f) + self.extractor.get_file_deletions(f)
            for f in files
        ]
        commit_additions = [self.extractor.get_commit_additions(c) for c in commits]
        commit_deletions = [self.extractor.get_commit_deletions(c) for c in commits]

        # --- PR/MR-level additions/deletions ---------------------------------
        if self.platform == "github":
            additions = self.extractor.get_pr_additions(details)
            deletions = self.extractor.get_pr_deletions(details)
        else:
            additions = sum(self.extractor.get_file_additions(f) for f in files)
            deletions = sum(self.extractor.get_file_deletions(f) for f in files)

        # --- Social data -----------------------------------------------------
        reviewers = self.adapter.get_reviewers(item)
        discussioners = self.adapter.get_discussioners(item)
        discussions_count = self.adapter.get_discussions_count(item)
        nb_comments = self.extractor.count_human_comments(item)

        # --- First review date (rework boundary) -----------------------------
        first_review_date = DataExtractor.parse_iso_date(
            self.extractor.get_first_review_date(item)
        )

        # --- Commit dates ----------------------------------------------------
        commit_dates = [
            DataExtractor.parse_iso_date(self.extractor.get_commit_date(c))
            for c in commits
        ]
        commit_dates = [d for d in commit_dates if d]

        # --- Metrics ---------------------------------------------------------
        lead_time = MetricsCalculator.calculate_lead_time(created_at, closed_at)
        mean_time_commits = MetricsCalculator.calculate_mean_time_between_commits(
            commit_dates
        )
        nb_minor, nb_major = MetricsCalculator.calculate_author_contributions(
            author_counts
        )
        delta_time = MetricsCalculator.calculate_delta_time(
            created_at, project_created_at
        )
        churn_add, churn_del = MetricsCalculator.calculate_churn(
            commit_additions, commit_deletions
        )
        hist_entropy = MetricsCalculator.calculate_entropy(file_changes)
        rework_size = MetricsCalculator.calculate_rework_size(
            commits, first_review_date, self.extractor
        )

        # --- Initial size (commits up to MR creation) ------------------------
        initial_size = self._calculate_initial_size(commits, created_at)

        # --- People count ----------------------------------------------------
        people = set(committer_logins) | set(reviewers) | set(discussioners)

        # --- Lead time display -----------------------------------------------
        state = self.extractor.get_state(details)
        lead_time_display = (
            "open" if state in ("opened", "open") else (lead_time or 0)
        )

        return {
            "Project_ID": collection_plan.repository_id,
            self.item_id_column: self.extractor.get_item_id(details),
            "Creation_Date": created_at_str or "",
            "Lead_Time": lead_time_display,
            "#Discussions": discussions_count,
            "#Commits": len(commits),
            "Mean_Time_between_commits": mean_time_commits,
            # Commiter_Names kept for backward-compat; Commiters = same display names
            "Commiters": ", ".join(sorted(committer_names)) if committer_names else "",
            "Commiter_Names": ", ".join(sorted(committer_names)) if committer_names else "",
            "#UniqueCommiters": len(committer_logins),
            "nb_minor_author": nb_minor,
            "nb_major_author": nb_major,
            "delta_time": delta_time,
            "churn_addition": churn_add,
            "churn_deletions": churn_del,
            self.initial_size_column: initial_size,
            "hist_entropy": hist_entropy,
            "modified_files": len(files),
            "filetypes": self._get_filetypes(files),
            "state": state,
            "rework_size": rework_size,
            "Author": author,
            "Reviewers": ", ".join(sorted(reviewers)) if reviewers else "",
            "#people": len(people),
            "#reviewers": len(reviewers),
            "#commiters": len(committer_logins),
            "#discussionners": len(discussioners),
            "additions": additions,
            "deletions": deletions,
            "comments": nb_comments,
        }

    # =========================================================================
    # EXTRACTION HELPERS
    # =========================================================================

    def _extract_author(self, details: dict) -> str:
        """
        Return the PR/MR author identifier.

        - GitLab: details['author']['username']
        - GitHub: details['user']['login']
        Falls back to empty string if missing.
        """
        if self.platform == "gitlab":
            author_obj = details.get("author") or {}
            return author_obj.get("username", "")
        # GitHub stores the PR author in the 'user' field
        user_obj = details.get("user") or {}
        return user_obj.get("login", "")

    def _extract_committers(self, commits: list) -> tuple[set, set, dict]:
        """
        Return (committer_names, committer_logins, author_counts).

        committer_names  – display names from commit author_name (used in "Commiters" column)
        committer_logins – unique login/username identifiers   (used for #UniqueCommiters)
        author_counts    – login → commit count                (used for minor/major split)
        """
        committer_names: set = set()
        committer_logins: set = set()
        author_counts: dict = {}

        for commit in commits:
            name = self.extractor.get_commit_author_name(commit)
            login = self.extractor.get_commit_author_login(commit)

            if name:
                committer_names.add(name)

            key = login or name
            if key:
                committer_logins.add(key)
                author_counts[key] = author_counts.get(key, 0) + 1

        return committer_names, committer_logins, author_counts

    def _calculate_initial_size(self, commits: list, created_at) -> int:
        """Lines changed in commits authored before or at MR/PR creation."""
        total = 0
        for commit in commits:
            commit_date = DataExtractor.parse_iso_date(
                self.extractor.get_commit_date(commit)
            )
            if commit_date is None:
                continue
            if created_at is None or commit_date <= created_at:
                total += self.extractor.get_commit_additions(commit)
                total += self.extractor.get_commit_deletions(commit)
        return total

    def _get_filetypes(self, files: list) -> str:
        """Return a sorted comma-separated string of unique file extensions across all changed files."""
        extensions = sorted({
            self.extractor.get_file_name(f).rsplit(".", 1)[-1].lower()
            for f in files
            if "." in self.extractor.get_file_name(f)
        })
        return ",".join(extensions)