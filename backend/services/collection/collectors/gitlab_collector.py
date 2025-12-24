import requests
from datetime import datetime
import logging
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class GitLabCollector:
    """
    Collects data from GitLab API based on MR_Extraction.py script
    """
    
    def __init__(self, token, repo_full_name, base_url='https://gitlab.com/api/v4', branch_name=None):
        self.token = token
        self.repo_full_name = repo_full_name
        self.branch_name = branch_name
        self.base_url = base_url
        self.headers = {'PRIVATE-TOKEN': token}
        self.project_id = None
    
    def collect_all_data(self, filters=None, progress_callback=None):
        """
        Collect all merge request data with progress updates
        
        Args:
            filters (dict): Date and status filters
            progress_callback (callable): Function to call with progress updates
        
        Returns:
            dict: All collected data organized by type
        """
        all_data = {
            'merge_requests': []
        }
        
        try:
            # Get project ID
            self.project_id = self._get_project_id()
            if not self.project_id:
                raise Exception("Could not get project ID")
            
            logger.info(f"Project ID: {self.project_id}")
            
            # First pass: Collect all MRs to get accurate count
            logger.info("Collecting MRs...")
            all_mrs = []
            page = 1
            
            while True:
                logger.info(f"Fetching page {page}")
                mrs = self._get_merge_requests_page(page, filters)
                
                if not mrs:
                    break
                
                all_mrs.extend(mrs)
                page += 1
                
                # Limit to 10 pages for now (200 MRs)
                if page > 10:
                    break
            
            # Now we have the accurate count
            total_mrs = len(all_mrs)
            logger.info(f"Total MRs to process: {total_mrs}")
            
            if progress_callback:
                progress_callback(0, total_mrs, "Starting collection...")
            
            # Process each MR
            collected_count = 0
            
            for mr in all_mrs:
                mr_data = self._process_merge_request(mr['iid'])
                if mr_data:
                    all_data['merge_requests'].append(mr_data)
                    collected_count += 1
                    
                    # Update progress
                    if progress_callback:
                        progress_callback(
                            collected_count,
                            total_mrs,
                            f"Collected MR !{mr['iid']}"
                        )
            
            logger.info(f"Collection completed: {collected_count} MRs")
            
            return all_data
            
        except Exception as e:
            logger.error(f"Error collecting data: {e}")
            raise
    
    def _get_project_id(self):
        """Get GitLab project ID from full name"""
        try:
            encoded_path = self.repo_full_name.replace('/', '%2F')
            response = requests.get(
                f"{self.base_url}/projects/{encoded_path}",
                headers=self.headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code == 200:
                return str(response.json()['id'])
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting project ID: {e}")
            return None
    
    def _get_merge_requests_page(self, page, filters=None):
        """Get one page of merge requests"""
        try:
            params = {
                'page': page,
                'per_page': 20
            }
            
            response = requests.get(
                f"{self.base_url}/projects/{self.project_id}/merge_requests",
                headers=self.headers,
                params=params,
                verify=False,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Error fetching MRs: {response.status_code}")
                return []
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error fetching MR page: {e}")
            return []
    
    def _process_merge_request(self, mr_iid):
        """
        Process a single merge request (like in MR_Extraction.py)
        """
        try:
            # Get MR details
            mr_response = requests.get(
                f"{self.base_url}/projects/{self.project_id}/merge_requests/{mr_iid}",
                headers=self.headers,
                verify=False,
                timeout=30
            )
            
            if mr_response.status_code != 200:
                logger.warning(f"Failed to fetch MR !{mr_iid}: {mr_response.status_code}")
                return None
            
            mr_details = mr_response.json()
            
            # Organize MR data
            organized_mr = {
                'merge_request_id': mr_iid,
                'details': mr_details,
                'commits': [],
                'discussions': [],
                'notes': [],
                'changes': []
            }
            
            # Get commits
            try:
                commits_response = requests.get(
                    f"{self.base_url}/projects/{self.project_id}/merge_requests/{mr_iid}/commits",
                    headers=self.headers,
                    params={'per_page': 9999},
                    verify=False,
                    timeout=30
                )
                
                if commits_response.status_code == 200:
                    commits = commits_response.json()
                    for commit in commits:
                        # Get commit diff
                        commit_diff = self._get_commit_diff(commit['short_id'])
                        organized_mr['commits'].append({
                            'commit_id': commit['short_id'],
                            'details': commit,
                            'changesHist': commit_diff
                        })
            except Exception as e:
                logger.warning(f"Error fetching commits for MR !{mr_iid}: {e}")
            
            # Get discussions
            try:
                discussions_response = requests.get(
                    f"{self.base_url}/projects/{self.project_id}/merge_requests/{mr_iid}/discussions",
                    headers=self.headers,
                    verify=False,
                    timeout=30
                )
                
                if discussions_response.status_code == 200:
                    organized_mr['discussions'] = discussions_response.json()
            except Exception as e:
                logger.warning(f"Error fetching discussions for MR !{mr_iid}: {e}")
            
            # Get notes
            try:
                notes_response = requests.get(
                    f"{self.base_url}/projects/{self.project_id}/merge_requests/{mr_iid}/notes",
                    headers=self.headers,
                    verify=False,
                    timeout=30
                )
                
                if notes_response.status_code == 200:
                    organized_mr['notes'] = notes_response.json()
            except Exception as e:
                logger.warning(f"Error fetching notes for MR !{mr_iid}: {e}")
            
            # Get changes
            try:
                changes_response = requests.get(
                    f"{self.base_url}/projects/{self.project_id}/merge_requests/{mr_iid}/changes",
                    headers=self.headers,
                    verify=False,
                    timeout=30
                )
                
                if changes_response.status_code == 200:
                    organized_mr['changes'] = changes_response.json()
            except Exception as e:
                logger.warning(f"Error fetching changes for MR !{mr_iid}: {e}")
            
            return organized_mr
            
        except Exception as e:
            logger.error(f"Error processing MR {mr_iid}: {e}")
            return None
    
    def _get_commit_diff(self, commit_id):
        """Get commit diff"""
        try:
            response = requests.get(
                f"{self.base_url}/projects/{self.project_id}/repository/commits/{commit_id}/diff",
                headers=self.headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            
            return []
            
        except Exception as e:
            logger.warning(f"Error getting commit diff for {commit_id}: {e}")
            return []