import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)


def _create_session(headers, max_retries=5, backoff_factor=1):
    """Create a requests.Session with retry + exponential backoff."""
    session = requests.Session()
    session.headers.update(headers)
    retry = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=['GET'],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session


class GitHubCollector:
    """Collects data from GitHub API with resume capability"""
    
    def __init__(self, token, repo_full_name, branch_name=None, selected_metrics=None):
        self.token = token
        self.repo_full_name = repo_full_name
        self.branch_name = branch_name
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        self.session = _create_session(self.headers)
        self.selected_metrics = selected_metrics
        self.required_endpoints = None  # Computed lazily
        self.project_created_at = None  # Fetched from API
    
    def collect_all_data(self, filters=None, progress_callback=None, resume_from=None, existing_data=None):
        """
        Collect all pull request data with progress updates and resume support

        Args:
            filters (dict): Date and status filters
            progress_callback (callable): Function to call with progress updates (current, total, message, item_data)
            resume_from (str): PR number to resume from (if resuming)
            existing_data (dict): Existing collected data (if resuming)

        Returns:
            dict: All collected data organized by type
        """
        if existing_data:
            all_data = existing_data
        else:
            all_data = {"pull_requests": []}

        self.is_total_approximate = False

        try:
            # Fetch project creation date
            try:
                repo_response = self.session.get(
                    f"{self.base_url}/repos/{self.repo_full_name}",
                    timeout=30
                )
                if repo_response.status_code == 200:
                    self.project_created_at = repo_response.json().get('created_at')
            except Exception as e:
                logger.warning(f"Could not fetch repo creation date: {e}")
            
            # Store project_created_at in the data for later use by CSV generator
            all_data['project_created_at'] = self.project_created_at

            # Get collected PR numbers to skip
            collected_prs = set()
            if existing_data:
                collected_prs = {
                    pr["pull_request_number"]
                    for pr in existing_data.get("pull_requests", [])
                }

            # Get total PR count upfront (GraphQL with Link header fallback)
            total_prs = self._get_total_pr_count(filters)
            has_date_filter = filters and (filters.get("start_date") or filters.get("end_date"))
            logger.info(f"Total PR count: {total_prs}")

            # Immediately report total so the frontend can display it during pagination
            if progress_callback and total_prs > 0:
                progress_callback(
                    len(collected_prs), total_prs, "Starting collection..."
                )

            # Process PRs page by page — no full pre-scan needed
            collected_count = len(collected_prs)
            failed_prs = []
            page = 1

            while True:
                logger.info(f"Fetching page {page}")
                prs = self._get_pull_requests_page(page, filters)

                if not prs:
                    logger.info(f"No more PRs found on page {page}")
                    break

                logger.info(f"Found {len(prs)} PRs on page {page}")

                for pr in prs:
                    # Skip already collected PRs (resume support)
                    if pr['number'] in collected_prs:
                        continue

                    # Apply date filter (GitHub API doesn't support date filtering on pulls endpoint)
                    if has_date_filter:
                        pr_created = pr.get('created_at', '')
                        if pr_created:
                            pr_date = datetime.fromisoformat(pr_created.replace('Z', '+00:00')).date()
                            if filters.get("start_date") and pr_date < filters["start_date"]:
                                continue
                            if filters.get("end_date") and pr_date > filters["end_date"]:
                                continue

                    try:
                        pr_data = self._process_pull_request(pr['number'])
                    except Exception as e:
                        logger.warning(f"Skipping PR #{pr['number']} due to error: {e}")
                        failed_prs.append(pr['number'])
                        continue

                    if pr_data:
                        all_data["pull_requests"].append(pr_data)
                        collected_count += 1

                        # Update progress with item data for incremental saving
                        if progress_callback:
                            progress_callback(
                                collected_count,
                                total_prs,
                                f"Collected PR #{pr['number']}",
                                pr_data,
                                all_data
                            )

                page += 1
            
            if failed_prs:
                logger.warning(f"Failed to collect {len(failed_prs)} PRs: {failed_prs}")

            # Update total_prs to actual count now that we've seen all pages
            total_prs = collected_count
            if progress_callback:
                progress_callback(
                    collected_count, total_prs, "Finalizing..."
                )
            
            # Deduplicate PRs by pull_request_number as a safety net
            seen = {}
            for pr in all_data['pull_requests']:
                seen[pr['pull_request_number']] = pr
            all_data['pull_requests'] = list(seen.values())
            
            logger.info(f"Collection completed: {len(all_data['pull_requests'])} unique PRs")
            
            return all_data

        except Exception as e:
            logger.error(f"Error collecting data: {e}")
            raise

    def _get_total_pr_count(self, filters=None):
        """
        Get total PR count using GitHub GraphQL API for exact results.
        Falls back to Link header method if GraphQL fails.
        """
        try:
            return self._get_total_pr_count_graphql(filters)
        except Exception as e:
            logger.warning(f"GraphQL total count failed, falling back to Link header: {e}")
            return self._get_total_pr_count_link_header(filters)

    def _get_total_pr_count_graphql(self, filters=None):
        """Get exact PR count using GitHub GraphQL API."""
        graphql_url = "https://api.github.com/graphql"
        graphql_headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        has_date_filter = filters and (filters.get("start_date") or filters.get("end_date"))

        if has_date_filter:
            # Use search query for date-filtered counts
            query_parts = [f"repo:{self.repo_full_name}", "is:pr"]

            if self.branch_name:
                query_parts.append(f"base:{self.branch_name}")

            start = filters.get("start_date") if filters else None
            end = filters.get("end_date") if filters else None
            if start and end:
                s = start.isoformat() if hasattr(start, 'isoformat') else start
                e = end.isoformat() if hasattr(end, 'isoformat') else end
                query_parts.append(f"created:{s}..{e}")
            elif start:
                s = start.isoformat() if hasattr(start, 'isoformat') else start
                query_parts.append(f"created:>={s}")
            elif end:
                e = end.isoformat() if hasattr(end, 'isoformat') else end
                query_parts.append(f"created:<={e}")

            graphql_query = """
            query($searchQuery: String!) {
                search(query: $searchQuery, type: ISSUE) {
                    issueCount
                }
            }
            """
            variables = {"searchQuery": " ".join(query_parts)}

            response = self.session.post(
                graphql_url,
                json={"query": graphql_query, "variables": variables},
                headers=graphql_headers,
                timeout=30,
            )
            if response.status_code != 200:
                raise Exception(f"GitHub GraphQL HTTP {response.status_code}")

            data = response.json()
            if "errors" in data:
                raise Exception(f"GraphQL errors: {data['errors']}")

            return data["data"]["search"]["issueCount"]
        else:
            # No date filter - use repository.pullRequests.totalCount (exact)
            owner, name = self.repo_full_name.split("/", 1)
            graphql_query = """
            query($owner: String!, $name: String!, $baseRefName: String) {
                repository(owner: $owner, name: $name) {
                    pullRequests(baseRefName: $baseRefName) {
                        totalCount
                    }
                }
            }
            """
            variables = {"owner": owner, "name": name}
            if self.branch_name:
                variables["baseRefName"] = self.branch_name

            response = self.session.post(
                graphql_url,
                json={"query": graphql_query, "variables": variables},
                headers=graphql_headers,
                timeout=30,
            )
            if response.status_code != 200:
                raise Exception(f"GitHub GraphQL HTTP {response.status_code}")

            data = response.json()
            if "errors" in data:
                raise Exception(f"GraphQL errors: {data['errors']}")

            return data["data"]["repository"]["pullRequests"]["totalCount"]

    def _get_total_pr_count_link_header(self, filters=None):
        """Fallback: get total PR count using Link header pagination trick."""
        try:
            params = {
                'state': 'all',
                'per_page': 1,
                'page': 1,
            }
            if self.branch_name:
                params['base'] = self.branch_name

            response = self.session.get(
                f"{self.base_url}/repos/{self.repo_full_name}/pulls",
                params=params,
                timeout=30,
            )
            if response.status_code == 200:
                link_header = response.headers.get('Link', '')
                if link_header:
                    match = re.search(r'page=(\d+)>;\s*rel="last"', link_header)
                    if match:
                        return int(match.group(1))
                data = response.json()
                return len(data)
            return 0
        except Exception as e:
            logger.warning(f"Could not get total PR count via Link header: {e}")
            return 0

    def _get_pull_requests_page(self, page, filters=None):
        """Get one page of pull requests"""
        try:
            params = {
                'state': 'all',
                'per_page': 100,
                'page': page,
                'sort': 'created',
                'direction': 'desc',
            }

            # Apply branch filter
            if self.branch_name:
                params['base'] = self.branch_name
            
            response = self.session.get(
                f"{self.base_url}/repos/{self.repo_full_name}/pulls",
                params=params,
                timeout=30,
            )

            if response.status_code == 401:
                raise Exception(
                    "GitHub token invalid or expired. Please update the token in workspace settings."
                )

            if response.status_code == 404:
                raise Exception(f"Repository not found: {self.repo_full_name}")

            if response.status_code != 200:
                raise Exception(f"GitHub API error: {response.status_code}")

            return response.json()

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Network connection error: {e}")
            raise Exception(f"Network connection lost while fetching PRs: {str(e)}")
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout: {e}")
            raise Exception(f"Request timeout while fetching PRs: {str(e)}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching PR page: {e}")
            raise Exception(f"Network error connecting to GitHub: {str(e)}")
    
    def _needs_endpoint(self, endpoint_key):
        """Check if a given endpoint category is needed based on selected metrics."""
        if self.required_endpoints is None:
            return True
        return endpoint_key in self.required_endpoints

    def _process_pull_request(self, pr_number):
        """Process a single pull request - raises exception on network errors"""
        try:
            pr_response = self.session.get(
                f"{self.base_url}/repos/{self.repo_full_name}/pulls/{pr_number}",
                timeout=30
            )

            if pr_response.status_code == 401:
                raise Exception("GitHub token invalid or expired.")

            if pr_response.status_code != 200:
                logger.warning(
                    f"Failed to fetch PR #{pr_number}: {pr_response.status_code}"
                )
                raise Exception(
                    f"Failed to fetch PR #{pr_number}: HTTP {pr_response.status_code}"
                )

            pr_details = pr_response.json()

            organized_pr = {
                "pull_request_number": pr_number,
                "details": pr_details,
                "commits": [],
                "comments": [],
                "reviews": [],
                "review_comments": [],
                "files": [],
            }
            
            # Get commits (only if selected)
            if self._needs_endpoint('commits'):
                try:
                    commits_response = self.session.get(
                        f"{self.base_url}/repos/{self.repo_full_name}/pulls/{pr_number}/commits",
                        params={'per_page': 100},
                        timeout=30
                    )
                    
                    if commits_response.status_code == 200:
                        commits = commits_response.json()
                        for commit in commits:
                            commit_detail = self._get_commit_details(commit['sha'])
                            organized_pr['commits'].append({
                                'commit_sha': commit['sha'],
                                'details': commit,
                                'changes': commit_detail.get('files', []) if commit_detail else []
                            })
                except requests.exceptions.RequestException as e:
                    logger.error(f"Network error fetching commits for PR #{pr_number}: {e}")
                    raise Exception(f"Network error fetching commits for PR #{pr_number}: {str(e)}")
            
            # Get comments (only if selected)
            if self._needs_endpoint('comments'):
                try:
                    comments_response = self.session.get(
                        f"{self.base_url}/repos/{self.repo_full_name}/issues/{pr_number}/comments",
                        timeout=30
                    )
                    
                    if comments_response.status_code == 200:
                        organized_pr['comments'] = comments_response.json()
                except requests.exceptions.RequestException as e:
                    logger.error(f"Network error fetching comments for PR #{pr_number}: {e}")
                    raise Exception(f"Network error fetching comments for PR #{pr_number}: {str(e)}")
            
            # Get reviews (only if selected)
            if self._needs_endpoint('reviews'):
                try:
                    reviews_response = self.session.get(
                        f"{self.base_url}/repos/{self.repo_full_name}/pulls/{pr_number}/reviews",
                        timeout=30
                    )
                    
                    if reviews_response.status_code == 200:
                        organized_pr['reviews'] = reviews_response.json()
                except requests.exceptions.RequestException as e:
                    logger.error(f"Network error fetching reviews for PR #{pr_number}: {e}")
                    raise Exception(f"Network error fetching reviews for PR #{pr_number}: {str(e)}")
            
            # Get review comments (only if selected)
            if self._needs_endpoint('review_comments'):
                try:
                    review_comments_response = self.session.get(
                        f"{self.base_url}/repos/{self.repo_full_name}/pulls/{pr_number}/comments",
                        timeout=30
                    )
                    
                    if review_comments_response.status_code == 200:
                        organized_pr['review_comments'] = review_comments_response.json()
                except requests.exceptions.RequestException as e:
                    logger.error(f"Network error fetching review comments for PR #{pr_number}: {e}")
                    raise Exception(f"Network error fetching review comments for PR #{pr_number}: {str(e)}")
            
            # Get files changed (only if selected)
            if self._needs_endpoint('files'):
                try:
                    files_response = self.session.get(
                        f"{self.base_url}/repos/{self.repo_full_name}/pulls/{pr_number}/files",
                        timeout=30
                    )
                    
                    if files_response.status_code == 200:
                        organized_pr['files'] = files_response.json()
                except requests.exceptions.RequestException as e:
                    logger.error(f"Network error fetching files for PR #{pr_number}: {e}")
                    raise Exception(f"Network error fetching files for PR #{pr_number}: {str(e)}")
            
            return organized_pr

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Network connection lost processing PR #{pr_number}: {e}")
            raise Exception(f"Network connection lost while processing PR #{pr_number}")
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout processing PR #{pr_number}: {e}")
            raise Exception(f"Request timeout while processing PR #{pr_number}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error processing PR {pr_number}: {e}")
            raise Exception(f"Network error processing PR #{pr_number}: {str(e)}")

    def _get_commit_details(self, commit_sha):
        """Get commit details with file changes"""
        try:
            response = self.session.get(
                f"{self.base_url}/repos/{self.repo_full_name}/commits/{commit_sha}",
                timeout=30
            )

            if response.status_code == 200:
                return response.json()

            return None

        except Exception as e:
            logger.warning(f"Error getting commit details for {commit_sha}: {e}")
            return None
