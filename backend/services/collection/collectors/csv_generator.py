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
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None
    
    @staticmethod
    def format_date(date_str: Optional[str]) -> str:
        """Format ISO date to readable string"""
        if not date_str:
            return ''
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return date_str


class GitHubDataExtractor(DataExtractor):
    """Extract data from GitHub Pull Request JSON format"""
    
    @staticmethod
    def get_item_key() -> str:
        return 'pull_requests'
    
    @staticmethod
    def get_item_id(details: dict) -> Optional[int]:
        """Get PR number"""
        return details.get('number')
    
    @staticmethod
    def get_title(details: dict) -> str:
        return details.get('title', '')
    
    @staticmethod
    def get_author(details: dict) -> str:
        """Get PR author login"""
        return details.get('user', {}).get('login', '')
    
    @staticmethod
    def get_state(details: dict) -> str:
        """Get PR state (open, closed, merged)"""
        if details.get('merged'):
            return 'merged'
        return details.get('state', '')
    
    @staticmethod
    def get_created_at(details: dict) -> Optional[str]:
        return details.get('created_at')
    
    @staticmethod
    def get_merged_at(details: dict) -> Optional[str]:
        return details.get('merged_at')
    
    @staticmethod
    def get_closed_at(details: dict) -> Optional[str]:
        return details.get('closed_at')
    
    @staticmethod
    def get_merged_by(details: dict) -> str:
        merged_by = details.get('merged_by')
        return merged_by.get('login', '') if merged_by else ''
    
    @staticmethod
    def get_commits(item: dict) -> List[dict]:
        """Get list of commits from PR"""
        return item.get('commits', [])
    
    @staticmethod
    def get_commit_sha(commit: dict) -> str:
        """Get commit SHA"""
        return commit.get('commit_sha', '') or commit.get('sha', '')
    
    @staticmethod
    def get_commit_author_name(commit: dict) -> str:
        """Extract commit author name from GitHub commit structure"""
        # Structure: commit.details.commit.author.name
        details = commit.get('details', {})
        return details.get('commit', {}).get('author', {}).get('name', '')
    
    @staticmethod
    def get_commit_author_login(commit: dict) -> str:
        """Extract commit author login from GitHub commit structure"""
        # Structure: commit.details.author.login
        details = commit.get('details', {})
        return details.get('author', {}).get('login', '')
    
    @staticmethod
    def get_commit_date(commit: dict) -> Optional[str]:
        """Extract commit date from GitHub commit structure"""
        # Structure: commit.details.commit.author.date
        details = commit.get('details', {})
        return details.get('commit', {}).get('author', {}).get('date')
    
    @staticmethod
    def get_commit_message(commit: dict) -> str:
        """Extract commit message from GitHub commit structure"""
        details = commit.get('details', {})
        return details.get('commit', {}).get('message', '')
    
    @staticmethod
    def get_commit_additions(commit: dict) -> int:
        """Get additions from commit changes"""
        changes = commit.get('changes', [])
        return sum(c.get('additions', 0) or 0 for c in changes)
    
    @staticmethod
    def get_commit_deletions(commit: dict) -> int:
        """Get deletions from commit changes"""
        changes = commit.get('changes', [])
        return sum(c.get('deletions', 0) or 0 for c in changes)
    
    @staticmethod
    def get_files(item: dict) -> List[dict]:
        """Get list of modified files"""
        return item.get('files', [])
    
    @staticmethod
    def get_file_name(file: dict) -> str:
        return file.get('filename', '')
    
    @staticmethod
    def get_file_additions(file: dict) -> int:
        return file.get('additions', 0) or 0
    
    @staticmethod
    def get_file_deletions(file: dict) -> int:
        return file.get('deletions', 0) or 0
    
    @staticmethod
    def get_pr_additions(details: dict) -> int:
        """Get total additions from PR details"""
        return details.get('additions', 0) or 0
    
    @staticmethod
    def get_pr_deletions(details: dict) -> int:
        """Get total deletions from PR details"""
        return details.get('deletions', 0) or 0
    
    @staticmethod
    def get_comments(item: dict) -> List[dict]:
        """Get issue comments"""
        return item.get('comments', [])
    
    @staticmethod
    def get_reviews(item: dict) -> List[dict]:
        """Get PR reviews"""
        return item.get('reviews', [])
    
    @staticmethod
    def get_review_comments(item: dict) -> List[dict]:
        """Get review comments (inline code comments)"""
        return item.get('review_comments', [])
    
    @staticmethod
    def get_comment_author(comment: dict) -> str:
        return comment.get('user', {}).get('login', '')
    
    @staticmethod
    def get_review_author(review: dict) -> str:
        return review.get('user', {}).get('login', '')
    
    @staticmethod
    def get_unique_reviewers(item: dict) -> Set[str]:
        """Get set of unique reviewers"""
        reviewers = set()
        for review in item.get('reviews', []):
            user = review.get('user', {}).get('login')
            if user:
                reviewers.add(user)
        return reviewers
    
    @staticmethod
    def get_unique_discussioners(item: dict) -> Set[str]:
        """Get set of unique users who participated in discussions"""
        discussioners = set()
        
        for comment in item.get('comments', []):
            user = comment.get('user', {}).get('login')
            if user:
                discussioners.add(user)
        
        for review in item.get('reviews', []):
            user = review.get('user', {}).get('login')
            if user:
                discussioners.add(user)
        
        for rc in item.get('review_comments', []):
            user = rc.get('user', {}).get('login')
            if user:
                discussioners.add(user)
        
        return discussioners


class GitLabDataExtractor(DataExtractor):
    """Extract data from GitLab Merge Request JSON format"""
    
    @staticmethod
    def get_item_key() -> str:
        return 'merge_requests'
    
    @staticmethod
    def get_item_id(details: dict) -> Optional[int]:
        """Get MR IID"""
        return details.get('iid')
    
    @staticmethod
    def get_title(details: dict) -> str:
        return details.get('title', '')
    
    @staticmethod
    def get_author(details: dict) -> str:
        """Get MR author username"""
        return details.get('author', {}).get('username', '')
    
    @staticmethod
    def get_state(details: dict) -> str:
        """Get MR state"""
        return details.get('state', '')
    
    @staticmethod
    def get_created_at(details: dict) -> Optional[str]:
        return details.get('created_at')
    
    @staticmethod
    def get_merged_at(details: dict) -> Optional[str]:
        return details.get('merged_at')
    
    @staticmethod
    def get_closed_at(details: dict) -> Optional[str]:
        return details.get('closed_at')
    
    @staticmethod
    def get_merged_by(details: dict) -> str:
        merged_by = details.get('merged_by')
        return merged_by.get('username', '') if merged_by else ''
    
    @staticmethod
    def get_commits(item: dict) -> List[dict]:
        """Get list of commits from MR"""
        return item.get('commits', [])
    
    @staticmethod
    def get_commit_sha(commit: dict) -> str:
        """Get commit SHA"""
        return commit.get('commit_id', '') or commit.get('id', '')
    
    @staticmethod
    def get_commit_author_name(commit: dict) -> str:
        """Extract commit author name from GitLab commit structure"""
        # Structure: commit.details.author_name
        details = commit.get('details', {})
        return details.get('author_name', '')
    
    @staticmethod
    def get_commit_author_login(commit: dict) -> str:
        """GitLab doesn't have login in commits, return author_name"""
        details = commit.get('details', {})
        return details.get('author_name', '')
    
    @staticmethod
    def get_commit_date(commit: dict) -> Optional[str]:
        """Extract commit date from GitLab commit structure"""
        # Structure: commit.details.authored_date or commit.details.created_at
        details = commit.get('details', {})
        return details.get('authored_date') or details.get('created_at')
    
    @staticmethod
    def get_commit_message(commit: dict) -> str:
        """Extract commit message from GitLab commit structure"""
        details = commit.get('details', {})
        return details.get('message', '') or details.get('title', '')
    
    @staticmethod
    def get_commit_additions(commit: dict) -> int:
        """
        Get additions from commit changesHist by parsing the diff.
        
        GitLab stores diffs in unified format. Lines starting with '+' 
        (but not '+++') are additions.
        """
        total_additions = 0
        for change in commit.get('changesHist', []):
            diff = change.get('diff', '')
            for line in diff.split('\n'):
                # Count lines that start with '+' but not '+++' (file header)
                if line.startswith('+') and not line.startswith('+++'):
                    total_additions += 1
        return total_additions
    
    @staticmethod
    def get_commit_deletions(commit: dict) -> int:
        """
        Get deletions from commit changesHist by parsing the diff.
        
        Lines starting with '-' (but not '---') are deletions.
        """
        total_deletions = 0
        for change in commit.get('changesHist', []):
            diff = change.get('diff', '')
            for line in diff.split('\n'):
                # Count lines that start with '-' but not '---' (file header)
                if line.startswith('-') and not line.startswith('---'):
                    total_deletions += 1
        return total_deletions
    
    @staticmethod
    def get_files(item: dict) -> List[dict]:
        """Get list of modified files from changes"""
        changes = item.get('changes', {})
        if isinstance(changes, dict):
            return changes.get('changes', []) or changes.get('diffs', [])
        return []
    
    @staticmethod
    def get_file_name(file: dict) -> str:
        return file.get('new_path', '') or file.get('old_path', '')
    
    @staticmethod
    def get_file_additions(file: dict) -> int:
        """Parse additions from file diff"""
        diff = file.get('diff', '')
        additions = 0
        for line in diff.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                additions += 1
        return additions
    
    @staticmethod
    def get_file_deletions(file: dict) -> int:
        """Parse deletions from file diff"""
        diff = file.get('diff', '')
        deletions = 0
        for line in diff.split('\n'):
            if line.startswith('-') and not line.startswith('---'):
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
        return item.get('discussions', [])
    
    @staticmethod
    def get_notes(item: dict) -> List[dict]:
        """Get notes (comments)"""
        return item.get('notes', [])
    
    @staticmethod
    def get_note_author(note: dict) -> str:
        return note.get('author', {}).get('username', '')
    
    @staticmethod
    def get_unique_reviewers(item: dict) -> Set[str]:
        """Get set of unique reviewers from notes"""
        reviewers = set()
        for note in item.get('notes', []):
            author = note.get('author', {}).get('username')
            if author:
                reviewers.add(author)
        return reviewers
    
    @staticmethod
    def get_unique_discussioners(item: dict) -> Set[str]:
        """Get set of unique users who participated in discussions"""
        discussioners = set()
        
        for discussion in item.get('discussions', []):
            for note in discussion.get('notes', []):
                author = note.get('author', {}).get('username')
                if author:
                    discussioners.add(author)
        
        for note in item.get('notes', []):
            author = note.get('author', {}).get('username')
            if author:
                discussioners.add(author)
        
        return discussioners


def get_data_extractor(platform: str):
    """Factory function to get the appropriate data extractor"""
    extractors = {
        'github': GitHubDataExtractor,
        'gitlab': GitLabDataExtractor,
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
    Pure calculation functions for code review metrics based on industry standards.
    These functions take already-extracted data and compute metrics.
    They are platform-agnostic and work with normalized data.
    
    Metrics Reference (Industry Standards):
    - Lead Time: Time from PR/MR creation to close/merge in HOURS (DORA metric standard)
    - Churn: Total lines added and deleted across all commits
    - Entropy: Shannon entropy H = -Σ(p*log2(p)) measuring distribution of changes across files
    - Mean Time Between Commits: Average time interval between consecutive commits in SECONDS
    - Author Contributions: Count of major (>=50% commits) vs minor (<50%) contributors
    - Delta Time: Time in SECONDS from first commit to PR/MR creation
    - Rework Size: Lines changed AFTER first review/comment
    """
    
    @staticmethod
    def calculate_lead_time(created_at: Optional[datetime], closed_at: Optional[datetime]) -> float:
        """
        Calculate lead time in HOURS (DORA metric standard).
        
        Lead Time = (closed_at - created_at) in hours
        
        Industry standard: Elite teams < 4h, High performers < 24h, Medium < 168h (1 week)
        
        Args:
            created_at: When the PR/MR was created
            closed_at: When the PR/MR was closed/merged
            
        Returns:
            Lead time in hours, or 0 if dates are invalid
        """
        if not created_at or not closed_at:
            return 0.0
        delta = closed_at - created_at
        return round(delta.total_seconds() / 3600, 2)  # Convert to HOURS
    
    @staticmethod
    def calculate_mean_time_between_commits(commit_dates: List[datetime]) -> float:
        """
        Calculate mean time between consecutive commits in SECONDS.
        
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
    def calculate_churn(additions: int, deletions: int) -> Tuple[float, float]:
        """
        Calculate code churn (total additions and deletions).
        
        Code churn represents the total volume of code changes in a PR/MR.
        High churn may indicate:
        - Large feature implementation
        - Refactoring
        - Multiple changes bundled together
        
        Industry practice: Use PR/MR level totals, not sum of individual commits
        (to avoid double-counting when commits modify the same lines)
        
        Args:
            additions: Total additions in PR/MR
            deletions: Total deletions in PR/MR
            
        Returns:
            Tuple of (total_additions, total_deletions)
        """
        return float(additions), float(deletions)
    
    @staticmethod
    def calculate_entropy(file_changes: List[int]) -> float:
        """
        Calculate Shannon entropy based on file modification distribution.
        
        Entropy measures how evenly changes are distributed across files:
        - Low entropy (→0): changes concentrated in few files (focused change)
        - High entropy (→log2(n)): changes spread across many files (scattered change)
        
        Formula: H = -Σ(p_i * log2(p_i))
        where p_i = changes_in_file_i / total_changes
        
        Used in research to predict:
        - Bug introduction risk (Hassan 2009)
        - Code review complexity
        - Testing effort required
        
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
    def calculate_author_contributions(author_commit_counts: Dict[str, int]) -> Tuple[int, int]:
        """
        Calculate minor and major author counts.
        
        Industry standard definition:
        - Major author: contributed >= 50% of commits (dominant contributor)
        - Minor author: contributed < 50% of commits
        
        This metric helps identify:
        - Knowledge distribution
        - Bus factor
        - Collaboration patterns
        
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
            # CORRECTED: Use >= 0.5 instead of > 0.5 (industry standard)
            if contribution_pct >= 0.5:
                nb_major += 1
            else:
                nb_minor += 1
        
        return nb_minor, nb_major
    
    @staticmethod
    def calculate_delta_time(created_at: Optional[datetime], first_commit_date: Optional[datetime]) -> float:
        """
        Calculate delta time: time from first commit to PR/MR creation in SECONDS.
        
        This metric indicates development workflow:
        - Positive value: commits made before PR creation (work-in-progress approach)
        - Negative value: commits made after PR creation (less common, may indicate forced pushes)
        - Small value: PR created immediately after first commit (quick workflow)
        
        Args:
            created_at: When the PR/MR was created
            first_commit_date: Date of the first commit
            
        Returns:
            Time in seconds from first commit to PR creation (can be negative)
        """
        if not created_at or not first_commit_date:
            return 0.0
        
        delta = created_at - first_commit_date
        return round(delta.total_seconds(), 2)
    
    @staticmethod
    def calculate_rework_size(commits_after_review: List[dict], extractor) -> float:
        """
        Calculate rework size: lines changed AFTER first review/discussion.
        
        Rework represents code changes made in response to review feedback.
        Industry definition: Changes made within 3 weeks after first review comment.
        
        High rework may indicate:
        - Thorough code review process
        - Initial code quality issues
        - Evolving requirements
        
        Args:
            commits_after_review: List of commits made after first review
            extractor: Data extractor to parse commit changes
            
        Returns:
            Total lines (additions + deletions) changed after first review
        """
        rework_additions = 0
        rework_deletions = 0
        
        for commit in commits_after_review:
            rework_additions += extractor.get_commit_additions(commit)
            rework_deletions += extractor.get_commit_deletions(commit)
        
        return float(rework_additions + rework_deletions)


class PlatformAdapter:
    """
    Abstract adapter for platform-specific data extraction.
    Provides a unified interface to access PR/MR data regardless of platform.
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


class GitHubAdapter(PlatformAdapter):
    """Adapter for GitHub Pull Requests"""
    
    def __init__(self):
        super().__init__('github')
    
    def get_item_key(self) -> str:
        return 'pull_requests'
    
    def get_item_id(self, details: dict):
        return details.get('number')
    
    def get_author(self, details: dict) -> str:
        return details.get('user', {}).get('login', '')
    
    def get_merged_by(self, details: dict) -> str:
        merged_by = details.get('merged_by')
        return merged_by.get('login', '') if merged_by else ''
    
    def get_discussions_count(self, item: dict) -> int:
        # GitHub: count all discussion activities
        return len(item.get('comments', [])) + len(item.get('reviews', [])) + len(item.get('review_comments', []))
    
    def get_reviewers(self, item: dict) -> set:
        reviewers = set()
        for review in item.get('reviews', []):
            user = review.get('user', {}).get('login')
            if user:
                reviewers.add(user)
        return reviewers
    
    def get_discussioners(self, item: dict) -> set:
        discussioners = set()
        
        # From comments
        for comment in item.get('comments', []):
            user = comment.get('user', {}).get('login')
            if user:
                discussioners.add(user)
        
        # From reviews
        for review in item.get('reviews', []):
            user = review.get('user', {}).get('login')
            if user:
                discussioners.add(user)
        
        # From review comments
        for rc in item.get('review_comments', []):
            user = rc.get('user', {}).get('login')
            if user:
                discussioners.add(user)
        
        return discussioners


class GitLabAdapter(PlatformAdapter):
    """Adapter for GitLab Merge Requests"""
    
    def __init__(self):
        super().__init__('gitlab')
    
    def get_item_key(self) -> str:
        return 'merge_requests'
    
    def get_item_id(self, details: dict):
        return details.get('iid')
    
    def get_author(self, details: dict) -> str:
        return details.get('author', {}).get('username', '')
    
    def get_merged_by(self, details: dict) -> str:
        merged_by = details.get('merged_by')
        return merged_by.get('username', '') if merged_by else ''
    
    def get_discussions_count(self, item: dict) -> int:
        # GitLab: count discussions and notes
        discussion_count = 0
        for discussion in item.get('discussions', []):
            discussion_count += len(discussion.get('notes', []))
        return discussion_count + len(item.get('notes', []))
    
    def get_reviewers(self, item: dict) -> set:
        reviewers = set()
        for note in item.get('notes', []):
            author = note.get('author', {}).get('username')
            if author and 'approve' in note.get('body', '').lower():
                reviewers.add(author)
        return reviewers
    
    def get_discussioners(self, item: dict) -> set:
        discussioners = set()
        
        for discussion in item.get('discussions', []):
            for note in discussion.get('notes', []):
                author = note.get('author', {}).get('username')
                if author:
                    discussioners.add(author)
        
        for note in item.get('notes', []):
            author = note.get('author', {}).get('username')
            if author:
                discussioners.add(author)
        
        return discussioners


def get_platform_adapter(platform: str):
    """Factory function to get the appropriate platform adapter"""
    adapters = {
        'github': GitHubAdapter,
        'gitlab': GitLabAdapter,
    }
    adapter_class = adapters.get(platform.lower())
    if not adapter_class:
        raise ValueError(f"Unsupported platform: {platform}")
    return adapter_class()


# =============================================================================
# STATISTICS GENERATOR
# =============================================================================

class StatisticsCSVGenerator:
    """
    Generate statistics CSV with industry-standard metrics.
    
    Metrics are calculated according to software engineering research and industry best practices:
    - Lead Time: DORA metric standard (hours)
    - Code Churn: Industry standard (total changes)
    - Entropy: Shannon entropy from information theory
    - Rework: Based on code review research (changes after first review)
    """
    
    # All available features with their internal column names
    ALL_FEATURES = [
        'Creation_Date', 'Lead_Time', '#Discussions', '#Commits',
        'Mean_Time_between_commits', 'Commiters', '#UniqueCommiters',
        'nb_minor_author', 'nb_major_author', 'delta_time',
        'churn_addition', 'churn_deletions', 'initial_size',
        'hist_entropy', 'modified_files', 'filetypes', 'state',
        'rework_size', '#people', '#reviewers', '#commiters',
        '#discussionners', 'additions', 'deletions', 'comments'
    ]
    
    def __init__(self, platform: str):
        self.platform = platform
        self.extractor = get_data_extractor(platform)
        self.adapter = get_platform_adapter(platform)
        self.item_key = self.extractor.get_item_key()
        self.item_id_column = 'PR_ID' if platform == 'github' else 'MR_ID'
        self.initial_size_column = 'initial_pr_size' if platform == 'github' else 'initial_mr_size'
    
    def generate_statistics_csv(self, data: dict, collection_plan, selected_features: List[str] = None) -> str:
        """
        Generate statistics CSV with metrics per PR/MR.
        
        Args:
            data: The filtered PR/MR data
            collection_plan: The collection plan with repository info
            selected_features: Optional list of feature IDs to include.
                             If None or empty, all features are included.
        """
        items = data.get(self.item_key, [])
        
        output = io.StringIO()
        
        # Build headers
        base_headers = ['Project_ID', self.item_id_column]
        
        all_feature_headers = [
            'Creation_Date', 'Lead_Time', '#Discussions', '#Commits',
            'Mean_Time_between_commits', 'Commiters', '#UniqueCommiters',
            'nb_minor_author', 'nb_major_author', 'delta_time',
            'churn_addition', 'churn_deletions', self.initial_size_column,
            'hist_entropy', 'modified_files', 'filetypes', 'state',
            'rework_size', '#people', '#reviewers', '#commiters',
            '#discussionners', 'additions', 'deletions', 'comments'
        ]
        
        # Use all features if none selected
        feature_headers = all_feature_headers
        headers = base_headers + feature_headers
        
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        
        for item in items:
            row = self._build_row(item, collection_plan)
            # Filter row to only include selected headers
            filtered_row = {k: v for k, v in row.items() if k in headers}
            writer.writerow(filtered_row)
        
        return output.getvalue()
    
    def _build_row(self, item: dict, collection_plan) -> dict:
        """
        Build a single statistics row using industry-standard calculations.
        """
        details = item.get('details', {})
        commits = self.extractor.get_commits(item)
        
        # =====================================================================
        # STEP 1: DATA EXTRACTION
        # =====================================================================
        
        # Basic info
        item_id = self.extractor.get_item_id(details)
        state = self.extractor.get_state(details)
        created_at_str = self.extractor.get_created_at(details)
        closed_at_str = self.extractor.get_closed_at(details) or self.extractor.get_merged_at(details)
        
        # Parse dates
        created_at = DataExtractor.parse_iso_date(created_at_str)
        closed_at = DataExtractor.parse_iso_date(closed_at_str)
        
        # Extract commit information
        commit_dates = []
        author_counts = {}
        
        for commit in commits:
            # Commit date
            date_str = self.extractor.get_commit_date(commit)
            parsed_date = DataExtractor.parse_iso_date(date_str)
            if parsed_date:
                commit_dates.append(parsed_date)
            
            # Author counts
            author = self.extractor.get_commit_author_name(commit)
            if author:
                author_counts[author] = author_counts.get(author, 0) + 1
        
        committers = set(author_counts.keys())
        
        # Extract PR/MR level data
        files = self.extractor.get_files(item)
        
        if self.platform == 'github':
            additions = self.extractor.get_pr_additions(details)
            deletions = self.extractor.get_pr_deletions(details)
        else:
            # For GitLab, sum from files
            additions = sum(self.extractor.get_file_additions(f) for f in files)
            deletions = sum(self.extractor.get_file_deletions(f) for f in files)
        
        # Extract file changes for entropy
        file_changes = []
        for f in files:
            adds = self.extractor.get_file_additions(f)
            dels = self.extractor.get_file_deletions(f)
            file_changes.append(adds + dels)
        
        # Extract reviewers and discussioners
        reviewers = self.adapter.get_reviewers(item)
        discussioners = self.adapter.get_discussioners(item)
        discussions_count = self.adapter.get_discussions_count(item)
        
        # =====================================================================
        # STEP 2: CALCULATE METRICS USING INDUSTRY STANDARDS
        # =====================================================================
        
        # Lead time (HOURS - DORA standard)
        lead_time = MetricsCalculator.calculate_lead_time(created_at, closed_at)
        
        # Mean time between commits (SECONDS)
        mean_time_commits = MetricsCalculator.calculate_mean_time_between_commits(commit_dates)
        
        # Author contributions (>= 50% is major)
        nb_minor, nb_major = MetricsCalculator.calculate_author_contributions(author_counts)
        
        # Delta time (SECONDS from first commit to PR creation)
        first_commit_date = min(commit_dates) if commit_dates else None
        delta_time = MetricsCalculator.calculate_delta_time(created_at, first_commit_date)
        
        # Code churn (PR/MR level totals)
        churn_add, churn_del = MetricsCalculator.calculate_churn(additions, deletions)
        
        # Entropy (Shannon formula)
        hist_entropy = MetricsCalculator.calculate_entropy(file_changes)
        
        # Rework size (changes after first review)
        rework_size = self._calculate_rework_size(item, commits)
        
        # File type count
        filetypes = self._count_filetypes(files)
        
        # People count
        people = set(committers)
        people.update(discussioners)
        author = self.extractor.get_author(details)
        if author:
            people.add(author)
        people.update(reviewers)
        people_count = len(people)
        
        # =====================================================================
        # STEP 3: BUILD OUTPUT ROW
        # =====================================================================
        
        # Handle open PRs/MRs
        if state in ['opened', 'open']:
            lead_time_display = 'open'
        else:
            lead_time_display = lead_time if lead_time else 0
        
        initial_size = additions + deletions
        
        return {
            'Project_ID': collection_plan.repository_id,
            self.item_id_column: item_id,
            'Creation_Date': created_at_str or '',
            'Lead_Time': lead_time_display,
            '#Discussions': discussions_count,
            '#Commits': len(commits),
            'Mean_Time_between_commits': mean_time_commits,
            'Commiters': str(committers) if committers else 'set()',
            '#UniqueCommiters': len(committers),
            'nb_minor_author': nb_minor,
            'nb_major_author': nb_major,
            'delta_time': delta_time,
            'churn_addition': churn_add,
            'churn_deletions': churn_del,
            self.initial_size_column: initial_size,
            'hist_entropy': hist_entropy,
            'modified_files': len(files),
            'filetypes': filetypes,
            'state': state,
            'rework_size': rework_size,
            '#people': people_count,
            '#reviewers': len(reviewers),
            '#commiters': len(committers),
            '#discussionners': len(discussioners),
            'additions': additions,
            'deletions': deletions,
            'comments': discussions_count
        }
    
    def _calculate_rework_size(self, item: dict, commits: List[dict]) -> float:
        """
        Calculate rework size: changes made AFTER first review/comment.
        
        Industry definition: Code changes within 3 weeks after first review feedback.
        """
        details = item.get('details', {})
        created_at = DataExtractor.parse_iso_date(self.extractor.get_created_at(details))
        
        # Find the date of first review/discussion
        first_review_date = None
        
        # GitHub: check reviews
        for review in item.get('reviews', []):
            review_date = DataExtractor.parse_iso_date(review.get('submitted_at'))
            if review_date:
                if first_review_date is None or review_date < first_review_date:
                    first_review_date = review_date
        
        # GitHub: check review comments
        for rc in item.get('review_comments', []):
            comment_date = DataExtractor.parse_iso_date(rc.get('created_at'))
            if comment_date:
                if first_review_date is None or comment_date < first_review_date:
                    first_review_date = comment_date
        
        # GitHub: check issue comments
        for comment in item.get('comments', []):
            comment_date = DataExtractor.parse_iso_date(comment.get('created_at'))
            if comment_date:
                if first_review_date is None or comment_date < first_review_date:
                    first_review_date = comment_date
        
        # GitLab: check discussions
        for discussion in item.get('discussions', []):
            for note in discussion.get('notes', []):
                note_date = DataExtractor.parse_iso_date(note.get('created_at'))
                if note_date:
                    if first_review_date is None or note_date < first_review_date:
                        first_review_date = note_date
        
        # GitLab: check notes
        for note in item.get('notes', []):
            note_date = DataExtractor.parse_iso_date(note.get('created_at'))
            if note_date:
                if first_review_date is None or note_date < first_review_date:
                    first_review_date = note_date
        
        # If no review found, rework = 0
        if not first_review_date or not created_at:
            return 0.0
        
        # Count changes in commits after first review
        commits_after_review = []
        for commit in commits:
            commit_date = DataExtractor.parse_iso_date(self.extractor.get_commit_date(commit))
            
            if commit_date and commit_date > first_review_date:
                # Industry standard: only count commits within 3 weeks of first review
                days_after_review = (commit_date - first_review_date).days
                if days_after_review <= 21:  # 3 weeks
                    commits_after_review.append(commit)
        
        # Calculate rework using the MetricsCalculator
        return MetricsCalculator.calculate_rework_size(commits_after_review, self.extractor)
    
    def _count_filetypes(self, files: List) -> int:
        """Count unique file types/extensions"""
        extensions = set()
        for file in files:
            filename = self.extractor.get_file_name(file)
            if '.' in filename:
                ext = filename.rsplit('.', 1)[-1].lower()
                extensions.add(ext)
        return len(extensions)


# =============================================================================
# CSV GENERATOR FOR BASIC DATA EXPORT
# =============================================================================

class CSVGenerator:
    """Generate basic CSV from collected data with filters"""
    
    def __init__(self, platform: str):
        self.platform = platform
        self.item_key = 'pull_requests' if platform == 'github' else 'merge_requests'
    
    def apply_filters(self, raw_data: dict, filters: dict) -> dict:
        """Apply filters to raw data"""
        items = raw_data.get(self.item_key, [])
        filtered_items = []
        
        for item in items:
            # Filter by file extensions
            if filters.get('file_extensions'):
                files = item.get('files', [])
                has_extension = False
                
                for file in files:
                    filename = file.get('filename') or file.get('new_path')
                    if filename:
                        for ext in filters['file_extensions']:
                            if filename.endswith(ext):
                                has_extension = True
                                break
                
                if not has_extension:
                    continue
            
            # Filter by authors
            if filters.get('authors'):
                author = item.get('details', {}).get('user', {}).get('login') or \
                        item.get('details', {}).get('author', {}).get('username')
                
                if author not in filters['authors']:
                    continue
            
            # Filter by keyword_filters (new format: array of {field, keywords})
            keyword_filters = filters.get('keyword_filters', [])
            if keyword_filters:
                passes_all_keyword_filters = True
                
                for kf in keyword_filters:
                    keyword_field = kf.get('field')
                    keywords = kf.get('keywords', [])
                    
                    if not keyword_field or not keywords:
                        continue
                    
                    text_to_search = self._get_text_for_keyword_field(item, keyword_field)
                    has_keyword = any(keyword.lower() in text_to_search for keyword in keywords)
                    
                    if not has_keyword:
                        passes_all_keyword_filters = False
                        break
                
                if not passes_all_keyword_filters:
                    continue
            
            # Legacy support: Filter by keywords (old format: single keyword_field + keywords)
            elif filters.get('keywords') and filters.get('keyword_field'):
                keyword_field = filters['keyword_field']
                keywords = filters['keywords']
                
                text_to_search = self._get_text_for_keyword_field(item, keyword_field)
                has_keyword = any(keyword.lower() in text_to_search for keyword in keywords)
                
                if not has_keyword:
                    continue
            
            filtered_items.append(item)
        
        return {self.item_key: filtered_items}
    
    def _get_text_for_keyword_field(self, item: dict, keyword_field: str) -> str:
        """Extract text to search based on keyword field"""
        if keyword_field == 'title':
            return item.get('details', {}).get('title', '').lower()
        elif keyword_field == 'description':
            return item.get('details', {}).get('body', '').lower()
        elif keyword_field == 'comments':
            comments = item.get('comments', []) + item.get('notes', [])
            return " ".join([c.get('body', '').lower() for c in comments])
        elif keyword_field == 'commit_message':
            commits = item.get('commits', [])
            commit_messages = []
            for commit in commits:
                # GitHub format - nested under details.commit.message
                if 'details' in commit:
                    details = commit.get('details', {})
                    if 'commit' in details and 'message' in details.get('commit', {}):
                        commit_messages.append(details['commit']['message'].lower())
                    elif 'message' in details:
                        commit_messages.append(details['message'].lower())
                # Alternative GitHub format - directly under commit.message
                elif 'commit' in commit and 'message' in commit.get('commit', {}):
                    commit_messages.append(commit['commit']['message'].lower())
                # GitLab format - message directly in commit
                elif 'message' in commit:
                    commit_messages.append(commit['message'].lower())
                elif 'title' in commit:
                    commit_messages.append(commit['title'].lower())
            return " ".join(commit_messages)
        return ""
    
    def generate_preview(self, data: dict, rows: int = 5) -> List[dict]:
        """Generate preview of filtered data"""
        items = data.get(self.item_key, [])[:rows]
        preview = []
        
        for item in items:
            details = item.get('details', {})
            
            if self.platform == 'github':
                preview.append({
                    'PR_Number': details.get('number'),
                    'Title': details.get('title', ''),
                    'Author': details.get('user', {}).get('login', ''),
                    'Status': details.get('state', ''),
                    'Creation_Date': self._format_date(details.get('created_at')),
                    'Comments': len(item.get('comments', []))
                })
            else:
                preview.append({
                    'MR_IID': details.get('iid'),
                    'Title': details.get('title', ''),
                    'Author': details.get('author', {}).get('username', ''),
                    'Status': details.get('state', ''),
                    'Creation_Date': self._format_date(details.get('created_at')),
                    'Notes': len(item.get('notes', []))
                })
        
        return preview
    
    def generate_csv(self, data: dict) -> str:
        """Generate basic CSV content from filtered data"""
        items = data.get(self.item_key, [])
        
        output = io.StringIO()
        
        if self.platform == 'github':
            headers = [
                'PR_Number', 'Title', 'Author', 'Status', 'State',
                'Creation_Date', 'Merge_Date', 'Close_Date', 'Merged_By',
                'Commits_Count', 'Comments_Count', 'Reviews_Count',
                'Review_Comments_Count', 'Files_Changed', 'Additions', 'Deletions'
            ]
        else:
            headers = [
                'MR_IID', 'Title', 'Author', 'Status', 'State',
                'Creation_Date', 'Merge_Date', 'Close_Date', 'Merged_By',
                'Commits_Count', 'Notes_Count', 'Discussions_Count',
                'Files_Changed', 'Additions', 'Deletions'
            ]
        
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        
        for item in items:
            details = item.get('details', {})
            
            if self.platform == 'github':
                row = {
                    'PR_Number': details.get('number'),
                    'Title': details.get('title', ''),
                    'Author': details.get('user', {}).get('login', ''),
                    'Status': details.get('state', ''),
                    'State': 'merged' if details.get('merged') else details.get('state'),
                    'Creation_Date': self._format_date(details.get('created_at')),
                    'Merge_Date': self._format_date(details.get('merged_at')),
                    'Close_Date': self._format_date(details.get('closed_at')),
                    'Merged_By': details.get('merged_by', {}).get('login', '') if details.get('merged_by') else '',
                    'Commits_Count': len(item.get('commits', [])),
                    'Comments_Count': len(item.get('comments', [])),
                    'Reviews_Count': len(item.get('reviews', [])),
                    'Review_Comments_Count': len(item.get('review_comments', [])),
                    'Files_Changed': len(item.get('files', [])),
                    'Additions': details.get('additions', 0),
                    'Deletions': details.get('deletions', 0)
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
                    'Files_Changed': len(item.get('files', [])),
                    'Additions': 0,  # GitLab doesn't have direct totals
                    'Deletions': 0
                }
            
            writer.writerow(row)
        
        return output.getvalue()
    
    def _format_date(self, date_str: str) -> str:
        """Format ISO date to readable format"""
        if not date_str:
            return ''
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return date_str