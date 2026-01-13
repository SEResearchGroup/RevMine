import csv
import io
from datetime import datetime
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class CSVGenerator:
    """Generate structured CSV from collected data with filters"""
    
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
            
            # Filter by keywords
            if filters.get('keywords') and filters.get('keyword_field'):
                keyword_field = filters['keyword_field']
                keywords = filters['keywords']
                
                text_to_search = ""
                
                if keyword_field == 'title':
                    text_to_search = item.get('details', {}).get('title', '').lower()
                elif keyword_field == 'description':
                    text_to_search = item.get('details', {}).get('body', '').lower()
                elif keyword_field == 'comments':
                    comments = item.get('comments', []) + item.get('notes', [])
                    text_to_search = " ".join([c.get('body', '').lower() for c in comments])
                
                has_keyword = any(keyword.lower() in text_to_search for keyword in keywords)
                
                if not has_keyword:
                    continue
            
            filtered_items.append(item)
        
        return {self.item_key: filtered_items}
    
    def generate_csv(self, data: dict) -> str:
        """Generate CSV content from filtered data"""
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
                    'Files_Changed': len(item.get('changes', {}).get('diffs', [])) if item.get('changes') else 0,
                    'Additions': details.get('changes_count', '').split('+')[0] if details.get('changes_count') else 0,
                    'Deletions': details.get('changes_count', '').split('-')[-1] if details.get('changes_count') else 0
                }
            
            writer.writerow(row)
        
        return output.getvalue()
    
    def get_preview(self, data: dict, rows: int = 5) -> List[Dict]:
        """Get preview of first N rows"""
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
    
    def _format_date(self, date_str: str) -> str:
        """Format ISO date to readable format"""
        if not date_str:
            return ''
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
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
        # GitHub: count comments
        return len(item.get('comments', []))
    
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
    
    def get_files(self, item: dict) -> list:
        return item.get('files', [])
    
    def get_additions(self, details: dict) -> int:
        return details.get('additions', 0) or 0
    
    def get_deletions(self, details: dict) -> int:
        return details.get('deletions', 0) or 0
    
    def get_commit_author(self, commit: dict) -> str:
        return commit.get('details', {}).get('commit', {}).get('author', {}).get('name', '')
    
    def get_commit_date(self, commit: dict) -> str:
        return commit.get('details', {}).get('commit', {}).get('author', {}).get('date', '')


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
        # GitLab: count discussions
        return len(item.get('discussions', []))
    
    def get_reviewers(self, item: dict) -> set:
        reviewers = set()
        for note in item.get('notes', []):
            author = note.get('author', {}).get('username')
            if author:
                reviewers.add(author)
        return reviewers
    
    def get_discussioners(self, item: dict) -> set:
        discussioners = set()
        
        # From discussions
        for discussion in item.get('discussions', []):
            for note in discussion.get('notes', []):
                author = note.get('author', {}).get('username')
                if author:
                    discussioners.add(author)
        
        # From notes
        for note in item.get('notes', []):
            author = note.get('author', {}).get('username')
            if author:
                discussioners.add(author)
        
        return discussioners
    
    def get_files(self, item: dict) -> list:
        changes = item.get('changes', {})
        if isinstance(changes, dict):
            return changes.get('changes', []) or changes.get('diffs', [])
        return []
    
    def get_additions(self, details: dict) -> int:
        changes_count = details.get('changes_count', '')
        if changes_count and '+' in str(changes_count):
            try:
                return int(str(changes_count).split('+')[0])
            except ValueError:
                pass
        return details.get('additions', 0) or 0
    
    def get_deletions(self, details: dict) -> int:
        changes_count = details.get('changes_count', '')
        if changes_count and '-' in str(changes_count):
            try:
                return int(str(changes_count).split('-')[-1])
            except ValueError:
                pass
        return details.get('deletions', 0) or 0
    
    def get_commit_author(self, commit: dict) -> str:
        return commit.get('details', {}).get('author_name', '')
    
    def get_commit_date(self, commit: dict) -> str:
        return commit.get('details', {}).get('authored_date', '')


def get_platform_adapter(platform: str) -> PlatformAdapter:
    """Factory function to get the appropriate platform adapter"""
    adapters = {
        'github': GitHubAdapter,
        'gitlab': GitLabAdapter,
    }
    adapter_class = adapters.get(platform.lower())
    if not adapter_class:
        raise ValueError(f"Unsupported platform: {platform}. Supported: {list(adapters.keys())}")
    return adapter_class()


class StatisticsCSVGenerator:
    """Generate project statistics CSV"""
    
    def __init__(self, platform: str):
        self.platform = platform
        self.adapter = get_platform_adapter(platform)
        self.item_key = self.adapter.get_item_key()
        self.item_id_column = 'PR_ID' if platform == 'github' else 'MR_ID'
        self.initial_size_column = 'initial_pr_size' if platform == 'github' else 'initial_mr_size'
    
    def generate_statistics_csv(self, data: dict, collection_plan) -> str:
        """Generate statistics CSV with metrics per PR/MR"""
        items = data.get(self.item_key, [])
        
        output = io.StringIO()
        
        # Headers matching the target format with dynamic column names
        headers = [
            'Project_ID', self.item_id_column, 'Creation_Date', 'Lead_Time',
            '#Discussions', '#Commits', 'Mean_Time_between_commits',
            'Commiters', '#UniqueCommiters', 'nb_minor_author', 'nb_major_author',
            'delta_time', 'churn_addition', 'churn_deletions', self.initial_size_column,
            'hist_entropy', 'modified_files', 'filetypes', 'state',
            'rework_size', '#people', '#reviewers', '#commiters',
            '#discussionners', 'additions', 'deletions', 'comments'
        ]
        
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        
        for item in items:
            row = self._build_row(item, collection_plan)
            writer.writerow(row)
        
        return output.getvalue()
    
    def _build_row(self, item: dict, collection_plan) -> dict:
        """Build a single row using the platform adapter"""
        details = item.get('details', {})
        commits = item.get('commits', [])
        
        # Parse dates
        created_at = self._parse_date(details.get('created_at'))
        closed_at = self._parse_date(details.get('closed_at') or details.get('merged_at'))
        
        # Calculate metrics
        lead_time = self._calculate_lead_time(created_at, closed_at)
        mean_time_commits = self._calculate_mean_time_between_commits(commits)
        committers = self._get_committers(commits)
        
        # Platform-specific data extraction via adapter
        item_id = self.adapter.get_item_id(details)
        discussions_count = self.adapter.get_discussions_count(item)
        reviewers = self.adapter.get_reviewers(item)
        discussioners = self.adapter.get_discussioners(item)
        files = self.adapter.get_files(item)
        additions = self.adapter.get_additions(details)
        deletions = self.adapter.get_deletions(details)
        
        # Calculate additional metrics
        initial_size = additions + deletions
        modified_files_count = len(files)
        filetypes = self._count_filetypes(files)
        
        # Calculate commit author statistics (minor/major)
        nb_minor, nb_major = self._calculate_author_contributions(commits)
        
        # Calculate delta_time (time from first commit to MR creation in seconds)
        delta_time = self._calculate_delta_time(commits, created_at)
        
        # Calculate churn (from commit changes)
        churn_add, churn_del = self._calculate_churn(commits)
        
        # Calculate entropy (normalized file changes)
        hist_entropy = self._calculate_entropy(files)
        
        # Calculate rework size (lines changed in review after initial submission)
        rework_size = self._calculate_rework_size(item)
        
        # Count unique people involved
        people_count = self._count_unique_people(item, committers, discussioners)
        
        # State - show 'open' for non-merged/non-closed
        state = details.get('state', '')
        if state in ['opened', 'open']:
            lead_time_display = 'open'
        else:
            lead_time_display = lead_time if lead_time else 0
        
        return {
            'Project_ID': collection_plan.repository_id,
            self.item_id_column: item_id,
            'Creation_Date': details.get('created_at', ''),
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
            'modified_files': modified_files_count,
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
    
    def _parse_date(self, date_str: str):
        """Parse ISO date string"""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            return None
    
    def _calculate_lead_time(self, created_at, closed_at):
        """Calculate lead time in minutes"""
        if not created_at or not closed_at:
            return 0
        delta = closed_at - created_at
        return round(delta.total_seconds() / 60, 2)  # Return in minutes like the example
    
    def _calculate_mean_time_between_commits(self, commits: List):
        """Calculate mean time between commits in seconds"""
        if len(commits) < 2:
            return 0
        
        dates = []
        for commit in commits:
            date_str = self.adapter.get_commit_date(commit)
            if date_str:
                try:
                    dates.append(datetime.fromisoformat(date_str.replace('Z', '+00:00')))
                except:
                    pass
        
        if len(dates) < 2:
            return 0
        
        dates.sort()
        time_diffs = [(dates[i+1] - dates[i]).total_seconds() for i in range(len(dates)-1)]
        return round(sum(time_diffs) / len(time_diffs), 2)
    
    def _get_committers(self, commits: List) -> set:
        """Get unique committers"""
        committers = set()
        for commit in commits:
            author = self.adapter.get_commit_author(commit)
            if author:
                committers.add(author)
        return committers
    
    def _calculate_author_contributions(self, commits: List) -> tuple:
        """
        Calculate minor and major author counts.
        Major author: contributed >= 50% of commits
        Minor author: contributed < 50% of commits
        """
        if not commits:
            return 0, 0
        
        author_counts = {}
        for commit in commits:
            author = self.adapter.get_commit_author(commit)
            if author:
                author_counts[author] = author_counts.get(author, 0) + 1
        
        total_commits = len(commits)
        if total_commits == 0:
            return 0, 0
        
        nb_minor = 0
        nb_major = 0
        
        for author, count in author_counts.items():
            contribution_pct = count / total_commits
            if contribution_pct >= 0.5:
                nb_major += 1
            else:
                nb_minor += 1
        
        return nb_minor, nb_major
    
    def _calculate_delta_time(self, commits: List, created_at) -> float:
        """Calculate delta time - typically days since epoch or similar metric"""
        if not created_at:
            return 0
        
        # Calculate as fractional days since a reference point (epoch)
        epoch = datetime(1970, 1, 1, tzinfo=created_at.tzinfo if created_at.tzinfo else None)
        if created_at.tzinfo is None:
            from datetime import timezone
            epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
            created_at = created_at.replace(tzinfo=timezone.utc)
        
        delta = created_at - epoch
        return round(delta.total_seconds() / 86400, 6)  # Days with precision
    
    def _calculate_churn(self, commits: List) -> tuple:
        """Calculate churn (total additions and deletions across all commits)"""
        total_additions = 0
        total_deletions = 0
        
        for commit in commits:
            changes = commit.get('changes', [])
            for change in changes:
                total_additions += change.get('additions', 0) or 0
                total_deletions += change.get('deletions', 0) or 0
            
            # Also try stats format
            stats = commit.get('details', {}).get('stats', {})
            if stats:
                total_additions += stats.get('additions', 0) or 0
                total_deletions += stats.get('deletions', 0) or 0
        
        # If no commit-level data, estimate from MR total
        if total_additions == 0 and total_deletions == 0:
            return 0.0, 0.0
        
        return float(total_additions), float(total_deletions)
    
    def _count_filetypes(self, files: List) -> int:
        """Count unique file types/extensions"""
        extensions = set()
        for file in files:
            filename = file.get('filename') or file.get('new_path') or file.get('old_path', '')
            if '.' in filename:
                ext = filename.rsplit('.', 1)[-1].lower()
                extensions.add(ext)
        return len(extensions)
    
    def _calculate_entropy(self, files: List) -> float:
        """
        Calculate historical entropy based on file modifications.
        Uses Shannon entropy formula on file change distribution.
        """
        import math
        
        if not files:
            return 0.0
        
        # Get changes per file
        changes = []
        for file in files:
            file_changes = (file.get('additions', 0) or 0) + (file.get('deletions', 0) or 0)
            if file_changes > 0:
                changes.append(file_changes)
        
        if not changes:
            return 0.0
        
        total = sum(changes)
        if total == 0:
            return 0.0
        
        entropy = 0.0
        for c in changes:
            if c > 0:
                p = c / total
                entropy -= p * math.log2(p) if p > 0 else 0
        
        return round(entropy, 6)
    
    def _calculate_rework_size(self, item: dict) -> float:
        """
        Calculate rework size - changes made after initial submission.
        This is approximated by looking at review comments and subsequent commits.
        """
        # Count additions/deletions mentioned in review comments or subsequent pushes
        rework = 0.0
        
        # Check review comments for suggested changes
        for rc in item.get('review_comments', []):
            # If there are review comments with code suggestions, estimate rework
            body = rc.get('body', '')
            if 'suggestion' in body.lower() or '```' in body:
                rework += 10.0  # Estimate per review comment with code
        
        # For GitLab, check discussions
        for discussion in item.get('discussions', []):
            for note in discussion.get('notes', []):
                if note.get('type') == 'DiffNote':
                    rework += 10.0
        
        return rework
    
    def _count_unique_people(self, item: dict, committers: set, discussioners: set) -> int:
        """Count total unique people involved in the MR/PR"""
        people = set()
        
        # Add committers
        people.update(committers)
        
        # Add discussioners
        people.update(discussioners)
        
        # Add author using adapter
        details = item.get('details', {})
        author = self.adapter.get_author(details)
        if author:
            people.add(author)
        
        return len(people)