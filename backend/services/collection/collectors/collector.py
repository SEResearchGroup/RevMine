import requests
from datetime import datetime
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class DataCollector:
    """
    Handles data collection from GitHub and GitLab APIs
    """
    
    def __init__(self, platform: str, token: str, repo_full_name: str):
        self.platform = platform
        self.token = token
        self.repo_full_name = repo_full_name
        self.base_url = self._get_base_url()
        self.headers = self._get_headers()
    
    def _get_base_url(self) -> str:
        """Get API base URL based on platform"""
        if self.platform == 'github':
            return 'https://api.github.com'
        elif self.platform == 'gitlab':
            return 'https://gitlab.com/api/v4'
        else:  # gitlab_self
            # For self-hosted, URL should be passed differently
            return 'https://gitlab.com/api/v4'
    
    def _get_headers(self) -> Dict:
        """Get authentication headers"""
        if self.platform == 'github':
            return {
                'Authorization': f'token {self.token}',
                'Accept': 'application/vnd.github.v3+json'
            }
        else:  # GitLab
            return {'PRIVATE-TOKEN': self.token}
    
    def collect_metric(self, metric_type: str, filters: Dict) -> List[Dict]:
        """
        Collect data for a specific metric
        """
        logger.info(f"Collecting {metric_type} for {self.repo_full_name}")
        
        if metric_type == 'pull_requests':
            return self._collect_pull_requests(filters)
        elif metric_type == 'commits':
            return self._collect_commits(filters)
        elif metric_type == 'issues':
            return self._collect_issues(filters)
        elif metric_type == 'comments':
            return self._collect_comments(filters)
        elif metric_type == 'reviews':
            return self._collect_reviews(filters)
        else:
            return []
    
    def _collect_pull_requests(self, filters: Dict) -> List[Dict]:
        """Collect pull requests / merge requests"""
        all_data = []
        
        if self.platform == 'github':
            endpoint = f"{self.base_url}/repos/{self.repo_full_name}/pulls"
            params = {'state': 'all', 'per_page': 100}
            
            # Apply status filter
            status_filter = filters.get('status', [])
            if status_filter:
                if 'open' in status_filter:
                    params['state'] = 'open'
                elif 'closed' in status_filter and 'merged' not in status_filter:
                    params['state'] = 'closed'
            
            all_data = self._paginate_github(endpoint, params)
            
            # Filter by date and merged status
            filtered_data = []
            for pr in all_data:
                if self._matches_filters(pr, filters, 'created_at'):
                    # Check merged status if needed
                    if 'merged' in status_filter and not pr.get('merged_at'):
                        continue
                    if 'closed' in status_filter and 'merged' not in status_filter and pr.get('merged_at'):
                        continue
                    filtered_data.append(pr)
            
            return filtered_data
        
        else:  # GitLab
            # Get project ID first
            project_id = self._get_gitlab_project_id()
            if not project_id:
                return []
            
            endpoint = f"{self.base_url}/projects/{project_id}/merge_requests"
            params = {'per_page': 100}
            
            # Apply status filter
            status_filter = filters.get('status', [])
            if status_filter:
                if 'open' in status_filter:
                    params['state'] = 'opened'
                elif 'closed' in status_filter:
                    params['state'] = 'closed'
                elif 'merged' in status_filter:
                    params['state'] = 'merged'
            
            all_data = self._paginate_gitlab(endpoint, params)
            
            # Filter by date
            return [mr for mr in all_data if self._matches_filters(mr, filters, 'created_at')]
    
    def _collect_commits(self, filters: Dict) -> List[Dict]:
        """Collect commits"""
        if self.platform == 'github':
            endpoint = f"{self.base_url}/repos/{self.repo_full_name}/commits"
            params = {'per_page': 100}
            
            # Apply date filters
            if filters.get('start_date'):
                params['since'] = filters['start_date'].isoformat()
            if filters.get('end_date'):
                params['until'] = filters['end_date'].isoformat()
            
            return self._paginate_github(endpoint, params)
        
        else:  # GitLab
            project_id = self._get_gitlab_project_id()
            if not project_id:
                return []
            
            endpoint = f"{self.base_url}/projects/{project_id}/repository/commits"
            params = {'per_page': 100}
            
            # Apply date filters
            if filters.get('start_date'):
                params['since'] = filters['start_date'].isoformat()
            if filters.get('end_date'):
                params['until'] = filters['end_date'].isoformat()
            
            return self._paginate_gitlab(endpoint, params)
    
    def _collect_issues(self, filters: Dict) -> List[Dict]:
        """Collect issues"""
        if self.platform == 'github':
            endpoint = f"{self.base_url}/repos/{self.repo_full_name}/issues"
            params = {'state': 'all', 'per_page': 100}
            
            all_data = self._paginate_github(endpoint, params)
            
            # Filter pull requests out (GitHub returns PRs as issues)
            issues = [item for item in all_data if 'pull_request' not in item]
            
            # Filter by date and status
            filtered = []
            for issue in issues:
                if self._matches_filters(issue, filters, 'created_at'):
                    status_filter = filters.get('status', [])
                    if status_filter:
                        if 'open' in status_filter and issue['state'] != 'open':
                            continue
                        if 'closed' in status_filter and issue['state'] != 'closed':
                            continue
                    filtered.append(issue)
            
            return filtered
        
        else:  # GitLab
            project_id = self._get_gitlab_project_id()
            if not project_id:
                return []
            
            endpoint = f"{self.base_url}/projects/{project_id}/issues"
            params = {'per_page': 100}
            
            all_data = self._paginate_gitlab(endpoint, params)
            return [issue for issue in all_data if self._matches_filters(issue, filters, 'created_at')]
    
    def _collect_comments(self, filters: Dict) -> List[Dict]:
        """Collect comments (PR/MR comments)"""
        all_comments = []
        
        # First get all PRs/MRs
        prs = self._collect_pull_requests(filters)
        
        if self.platform == 'github':
            for pr in prs:
                endpoint = f"{self.base_url}/repos/{self.repo_full_name}/issues/{pr['number']}/comments"
                comments = self._paginate_github(endpoint, {'per_page': 100})
                all_comments.extend(comments)
        
        else:  # GitLab
            project_id = self._get_gitlab_project_id()
            if not project_id:
                return []
            
            for mr in prs:
                endpoint = f"{self.base_url}/projects/{project_id}/merge_requests/{mr['iid']}/notes"
                notes = self._paginate_gitlab(endpoint, {'per_page': 100})
                all_comments.extend(notes)
        
        return all_comments
    
    def _collect_reviews(self, filters: Dict) -> List[Dict]:
        """Collect PR reviews (GitHub only)"""
        if self.platform != 'github':
            return []
        
        all_reviews = []
        prs = self._collect_pull_requests(filters)
        
        for pr in prs:
            endpoint = f"{self.base_url}/repos/{self.repo_full_name}/pulls/{pr['number']}/reviews"
            reviews = self._paginate_github(endpoint, {'per_page': 100})
            all_reviews.extend(reviews)
        
        return all_reviews
    
    def _get_gitlab_project_id(self) -> str:
        """Get GitLab project ID from full name"""
        try:
            encoded_path = self.repo_full_name.replace('/', '%2F')
            endpoint = f"{self.base_url}/projects/{encoded_path}"
            
            response = requests.get(endpoint, headers=self.headers, timeout=10)
            if response.status_code == 200:
                return str(response.json()['id'])
        except Exception as e:
            logger.error(f"Failed to get GitLab project ID: {e}")
        
        return None
    
    def _paginate_github(self, endpoint: str, params: Dict) -> List[Dict]:
        """Handle GitHub pagination"""
        all_data = []
        page = 1
        
        while True:
            params['page'] = page
            try:
                response = requests.get(endpoint, headers=self.headers, params=params, timeout=30)
                
                if response.status_code != 200:
                    logger.error(f"GitHub API error: {response.status_code}")
                    break
                
                data = response.json()
                if not data:
                    break
                
                all_data.extend(data)
                page += 1
                
                # Limit to 10 pages for now
                if page > 10:
                    break
                
            except Exception as e:
                logger.error(f"Error paginating GitHub: {e}")
                break
        
        return all_data
    
    def _paginate_gitlab(self, endpoint: str, params: Dict) -> List[Dict]:
        """Handle GitLab pagination"""
        all_data = []
        page = 1
        
        while True:
            params['page'] = page
            try:
                response = requests.get(endpoint, headers=self.headers, params=params, timeout=30)
                
                if response.status_code != 200:
                    logger.error(f"GitLab API error: {response.status_code}")
                    break
                
                data = response.json()
                if not data:
                    break
                
                all_data.extend(data)
                page += 1
                
                # Limit to 10 pages for now
                if page > 10:
                    break
                
            except Exception as e:
                logger.error(f"Error paginating GitLab: {e}")
                break
        
        return all_data
    
    def _matches_filters(self, item: Dict, filters: Dict, date_field: str) -> bool:
        """Check if item matches date filters"""
        start_date = filters.get('start_date')
        end_date = filters.get('end_date')
        
        if not start_date and not end_date:
            return True
        
        item_date_str = item.get(date_field)
        if not item_date_str:
            return True
        
        try:
            # Parse ISO date
            item_date = datetime.fromisoformat(item_date_str.replace('Z', '+00:00')).date()
            
            if start_date and item_date < start_date:
                return False
            if end_date and item_date > end_date:
                return False
            
            return True
        except Exception:
            return True