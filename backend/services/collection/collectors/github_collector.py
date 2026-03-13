import requests
import logging

logger = logging.getLogger(__name__)


class GitHubCollector:
    """Collects data from GitHub API with resume capability"""

    def __init__(self, token, repo_full_name, branch_name=None):
        self.token = token
        self.repo_full_name = repo_full_name
        self.branch_name = branch_name
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def collect_all_data(
        self, filters=None, progress_callback=None, resume_from=None, existing_data=None
    ):
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

        try:
            # Get collected PR numbers to skip
            collected_prs = set()
            if existing_data:
                collected_prs = {
                    pr["pull_request_number"]
                    for pr in existing_data.get("pull_requests", [])
                }

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

                if page > 10:
                    break

            # Filter out already collected PRs
            if resume_from:
                resume_pr_num = int(resume_from)
                all_prs = [pr for pr in all_prs if pr["number"] not in collected_prs]

            total_prs = len(all_prs) + len(collected_prs)
            logger.info(
                f"Total PRs to process: {len(all_prs)} (already collected: {len(collected_prs)})"
            )

            if progress_callback:
                progress_callback(
                    len(collected_prs), total_prs, "Starting collection..."
                )

            # Process each PR
            collected_count = len(collected_prs)

            for pr in all_prs:
                pr_data = self._process_pull_request(pr["number"])
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
                        )

            logger.info(f"Collection completed: {collected_count} PRs")

            return all_data

        except Exception as e:
            logger.error(f"Error collecting data: {e}")
            raise

    def _get_pull_requests_page(self, page, filters=None):
        """Get one page of pull requests"""
        try:
            params = {"state": "all", "per_page": 30, "page": page}

            response = requests.get(
                f"{self.base_url}/repos/{self.repo_full_name}/pulls",
                headers=self.headers,
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

    def _process_pull_request(self, pr_number):
        """Process a single pull request - raises exception on network errors"""
        try:
            pr_response = requests.get(
                f"{self.base_url}/repos/{self.repo_full_name}/pulls/{pr_number}",
                headers=self.headers,
                timeout=30,
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

            # Get commits
            try:
                commits_response = requests.get(
                    f"{self.base_url}/repos/{self.repo_full_name}/pulls/{pr_number}/commits",
                    headers=self.headers,
                    params={"per_page": 100},
                    timeout=30,
                )

                if commits_response.status_code == 200:
                    commits = commits_response.json()
                    for commit in commits:
                        commit_detail = self._get_commit_details(commit["sha"])
                        organized_pr["commits"].append(
                            {
                                "commit_sha": commit["sha"],
                                "details": commit,
                                "changes": (
                                    commit_detail.get("files", [])
                                    if commit_detail
                                    else []
                                ),
                            }
                        )
            except requests.exceptions.RequestException as e:
                logger.error(f"Network error fetching commits for PR #{pr_number}: {e}")
                raise Exception(
                    f"Network error fetching commits for PR #{pr_number}: {str(e)}"
                )

            # Get comments
            try:
                comments_response = requests.get(
                    f"{self.base_url}/repos/{self.repo_full_name}/issues/{pr_number}/comments",
                    headers=self.headers,
                    timeout=30,
                )

                if comments_response.status_code == 200:
                    organized_pr["comments"] = comments_response.json()
            except requests.exceptions.RequestException as e:
                logger.error(
                    f"Network error fetching comments for PR #{pr_number}: {e}"
                )
                raise Exception(
                    f"Network error fetching comments for PR #{pr_number}: {str(e)}"
                )

            # Get reviews
            try:
                reviews_response = requests.get(
                    f"{self.base_url}/repos/{self.repo_full_name}/pulls/{pr_number}/reviews",
                    headers=self.headers,
                    timeout=30,
                )

                if reviews_response.status_code == 200:
                    organized_pr["reviews"] = reviews_response.json()
            except requests.exceptions.RequestException as e:
                logger.error(f"Network error fetching reviews for PR #{pr_number}: {e}")
                raise Exception(
                    f"Network error fetching reviews for PR #{pr_number}: {str(e)}"
                )

            # Get review comments
            try:
                review_comments_response = requests.get(
                    f"{self.base_url}/repos/{self.repo_full_name}/pulls/{pr_number}/comments",
                    headers=self.headers,
                    timeout=30,
                )

                if review_comments_response.status_code == 200:
                    organized_pr["review_comments"] = review_comments_response.json()
            except requests.exceptions.RequestException as e:
                logger.error(
                    f"Network error fetching review comments for PR #{pr_number}: {e}"
                )
                raise Exception(
                    f"Network error fetching review comments for PR #{pr_number}: {str(e)}"
                )

            # Get files changed
            try:
                files_response = requests.get(
                    f"{self.base_url}/repos/{self.repo_full_name}/pulls/{pr_number}/files",
                    headers=self.headers,
                    timeout=30,
                )

                if files_response.status_code == 200:
                    organized_pr["files"] = files_response.json()
            except requests.exceptions.RequestException as e:
                logger.error(f"Network error fetching files for PR #{pr_number}: {e}")
                raise Exception(
                    f"Network error fetching files for PR #{pr_number}: {str(e)}"
                )

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
            response = requests.get(
                f"{self.base_url}/repos/{self.repo_full_name}/commits/{commit_sha}",
                headers=self.headers,
                timeout=30,
            )

            if response.status_code == 200:
                return response.json()

            return None

        except Exception as e:
            logger.warning(f"Error getting commit details for {commit_sha}: {e}")
            return None
