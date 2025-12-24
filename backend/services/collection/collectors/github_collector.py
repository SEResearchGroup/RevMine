import requests
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class GitHubCollector:
    """
    Collects data from GitHub API based on PR_Extraction.py script
    """
    
    def __init__(self, token, repo_full_name, branch_name=None):
        self.token = token
        self.repo_full_name = repo_full_name
        self.branch_name = branch_name
        self.base_url = 'https://api.github.com'
        self.headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
    
    def collect_all_data(self, filters=None, progress_callback=None):
        """
        Collect all pull request data with progress updates
        
        Args:
            filters (dict): Date and status filters
            progress_callback (callable): Function to call with progress updates
        
        Returns:
            dict: All collected data organized by type
        """
        all_data = {
            'pull_requests': []
        }
        
        try:
            # First pass: Collect all PRs to get accurate count
            logger.info("Collecting PRs...")
            all_prs = []
            page = 1
            
            while True:
                logger.info(f"Fetching page {page}")
                prs = self._get_pull_requests_page(page, filters)
                
                if not prs:
                    break
                
                all_prs.extend(prs)
                page += 1
                
                # Limit to 10 pages for now (300 PRs)
                if page > 10:
                    break
            
            # Now we have the accurate count
            total_prs = len(all_prs)
            logger.info(f"Total PRs to process: {total_prs}")
            
            if progress_callback:
                progress_callback(0, total_prs, "Starting collection...")
            
            # Process each PR
            collected_count = 0
            
            for pr in all_prs:
                pr_data = self._process_pull_request(pr['number'])
                if pr_data:
                    all_data['pull_requests'].append(pr_data)
                    collected_count += 1
                    
                    # Update progress
                    if progress_callback:
                        progress_callback(
                            collected_count, 
                            total_prs,
                            f"Collected PR #{pr['number']}"
                        )
            
            logger.info(f"Collection completed: {collected_count} PRs")
            
            return all_data
            
        except Exception as e:
            logger.error(f"Error collecting data: {e}")
            raise
    
    def _get_pull_requests_page(self, page, filters=None):
        """Get one page of pull requests"""
        try:
            params = {
                'state': 'all',
                'per_page': 30,
                'page': page
            }
            
            response = requests.get(
                f"{self.base_url}/repos/{self.repo_full_name}/pulls",
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Error fetching PRs: {response.status_code}")
                return []
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error fetching PR page: {e}")
            return []
    
    def _process_pull_request(self, pr_number):
        """
        Process a single pull request (like in PR_Extraction.py)
        """
        try:
            # Get PR details
            pr_response = requests.get(
                f"{self.base_url}/repos/{self.repo_full_name}/pulls/{pr_number}",
                headers=self.headers,
                timeout=30
            )
            
            if pr_response.status_code != 200:
                logger.warning(f"Failed to fetch PR #{pr_number}: {pr_response.status_code}")
                return None
            
            pr_details = pr_response.json()
            
            # Organize PR data
            organized_pr = {
                'pull_request_number': pr_number,
                'details': pr_details,
                'commits': [],
                'comments': [],
                'reviews': [],
                'review_comments': [],
                'files': []
            }
            
            # Get commits
            try:
                commits_response = requests.get(
                    f"{self.base_url}/repos/{self.repo_full_name}/pulls/{pr_number}/commits",
                    headers=self.headers,
                    params={'per_page': 100},
                    timeout=30
                )
                
                if commits_response.status_code == 200:
                    commits = commits_response.json()
                    for commit in commits:
                        # Get commit details
                        commit_detail = self._get_commit_details(commit['sha'])
                        organized_pr['commits'].append({
                            'commit_sha': commit['sha'],
                            'details': commit,
                            'changes': commit_detail.get('files', []) if commit_detail else []
                        })
            except Exception as e:
                logger.warning(f"Error fetching commits for PR #{pr_number}: {e}")
            
            # Get comments (issue comments)
            try:
                comments_response = requests.get(
                    f"{self.base_url}/repos/{self.repo_full_name}/issues/{pr_number}/comments",
                    headers=self.headers,
                    timeout=30
                )
                
                if comments_response.status_code == 200:
                    organized_pr['comments'] = comments_response.json()
            except Exception as e:
                logger.warning(f"Error fetching comments for PR #{pr_number}: {e}")
            
            # Get reviews
            try:
                reviews_response = requests.get(
                    f"{self.base_url}/repos/{self.repo_full_name}/pulls/{pr_number}/reviews",
                    headers=self.headers,
                    timeout=30
                )
                
                if reviews_response.status_code == 200:
                    organized_pr['reviews'] = reviews_response.json()
            except Exception as e:
                logger.warning(f"Error fetching reviews for PR #{pr_number}: {e}")
            
            # Get review comments
            try:
                review_comments_response = requests.get(
                    f"{self.base_url}/repos/{self.repo_full_name}/pulls/{pr_number}/comments",
                    headers=self.headers,
                    timeout=30
                )
                
                if review_comments_response.status_code == 200:
                    organized_pr['review_comments'] = review_comments_response.json()
            except Exception as e:
                logger.warning(f"Error fetching review comments for PR #{pr_number}: {e}")
            
            # Get files changed
            try:
                files_response = requests.get(
                    f"{self.base_url}/repos/{self.repo_full_name}/pulls/{pr_number}/files",
                    headers=self.headers,
                    timeout=30
                )
                
                if files_response.status_code == 200:
                    organized_pr['files'] = files_response.json()
            except Exception as e:
                logger.warning(f"Error fetching files for PR #{pr_number}: {e}")
            
            return organized_pr
            
        except Exception as e:
            logger.error(f"Error processing PR {pr_number}: {e}")
            return None
    
    def _get_commit_details(self, commit_sha):
        """Get commit details with file changes"""
        try:
            response = requests.get(
                f"{self.base_url}/repos/{self.repo_full_name}/commits/{commit_sha}",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            
            return None
            
        except Exception as e:
            logger.warning(f"Error getting commit details for {commit_sha}: {e}")
            return None