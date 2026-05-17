import requests
import logging

from .http_client import resolve_tls_verify

logger = logging.getLogger(__name__)


class BranchFetcher:
    """
    Handles fetching branches from Git APIs
    """

    def __init__(
        self, platform: str, token: str, repo_full_name: str, base_url: str = None
    ):
        self.platform = platform
        self.token = token
        self.repo_full_name = repo_full_name
        self.base_url = base_url or self._get_base_url()
        self.headers = self._get_headers()
        self.verify_tls = resolve_tls_verify("GITLAB_CA_BUNDLE", "REQUESTS_CA_BUNDLE")

    def _get_base_url(self) -> str:
        """Get API base URL based on platform"""
        if self.platform == "github":
            return "https://api.github.com"
        elif self.platform == "gitlab":
            return "https://gitlab.com/api/v4"
        else:  # gitlab_self
            return "https://gitlab.com/api/v4"  # Should be passed as parameter

    def _get_headers(self) -> dict:
        """Get authentication headers"""
        if self.platform == "github":
            return {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json",
            }
        else:  # GitLab
            return {"PRIVATE-TOKEN": self.token}

    def fetch_branches(self) -> list:
        """
        Fetch all branches from repository

        Returns:
            list: List of branch objects with name and other details
        """
        try:
            if self.platform == "github":
                return self._fetch_github_branches()
            else:
                return self._fetch_gitlab_branches()
        except Exception as e:
            logger.error(f"Error fetching branches: {e}")
            return []

    def _fetch_github_branches(self) -> list:
        """Fetch branches from GitHub"""
        endpoint = f"{self.base_url}/repos/{self.repo_full_name}/branches"

        try:
            response = requests.get(
                endpoint,
                headers=self.headers,
                params={"per_page": 100},
                timeout=30,
            )

            if response.status_code != 200:
                logger.error(f"GitHub API error: {response.status_code}")
                return []

            branches_data = response.json()

            branches = []
            for branch in branches_data:
                branches.append(
                    {
                        "name": branch.get("name"),
                        "sha": branch.get("commit", {}).get("sha"),
                        "protected": branch.get("protected", False),
                    }
                )

            return branches

        except Exception as e:
            logger.error(f"Error fetching GitHub branches: {e}")
            return []

    def _fetch_gitlab_branches(self) -> list:
        """Fetch branches from GitLab"""
        # Get project ID first
        project_id = self._get_gitlab_project_id()
        if not project_id:
            return []

        endpoint = f"{self.base_url}/projects/{project_id}/repository/branches"

        try:
            response = requests.get(
                endpoint,
                headers=self.headers,
                params={"per_page": 100},
                timeout=30,
                verify=self.verify_tls,
            )

            if response.status_code != 200:
                logger.error(f"GitLab API error: {response.status_code}")
                return []

            branches_data = response.json()

            branches = []
            for branch in branches_data:
                branches.append(
                    {
                        "name": branch.get("name"),
                        "sha": branch.get("commit", {}).get("id"),
                        "protected": branch.get("protected", False),
                        "default": branch.get("default", False),
                    }
                )

            return branches

        except Exception as e:
            logger.error(f"Error fetching GitLab branches: {e}")
            return []

    def _get_gitlab_project_id(self) -> str:
        """Get GitLab project ID from full name"""
        try:
            encoded_path = self.repo_full_name.replace("/", "%2F")
            endpoint = f"{self.base_url}/projects/{encoded_path}"

            response = requests.get(
                endpoint,
                headers=self.headers,
                timeout=10,
                verify=self.verify_tls,
            )
            if response.status_code == 200:
                return str(response.json()["id"])
        except Exception as e:
            logger.error(f"Failed to get GitLab project ID: {e}")

        return None

    def fetch_date_range(self) -> dict:
        """
        Fetch the global date range of MRs/PRs (oldest and newest created_at).
        Returns: {"first_date": "2020-01-15T...", "last_date": "2024-12-01T..."}
        """
        try:
            if self.platform == "github":
                return self._fetch_github_date_range()
            else:
                return self._fetch_gitlab_date_range()
        except Exception as e:
            logger.error(f"Error fetching date range: {e}")
            return {"first_date": None, "last_date": None}

    def _fetch_github_date_range(self) -> dict:
        """Fetch date range from GitHub (oldest and newest PR)."""
        result = {"first_date": None, "last_date": None}

        # Newest PR (most recently created)
        try:
            response = requests.get(
                f"{self.base_url}/repos/{self.repo_full_name}/pulls",
                headers=self.headers,
                params={"state": "all", "sort": "created", "direction": "desc", "per_page": 1},
                timeout=30,
            )
            if response.status_code == 200:
                data = response.json()
                if data:
                    result["last_date"] = data[0].get("created_at")
        except Exception as e:
            logger.warning(f"Error fetching newest GitHub PR: {e}")

        # Oldest PR (earliest created)
        try:
            response = requests.get(
                f"{self.base_url}/repos/{self.repo_full_name}/pulls",
                headers=self.headers,
                params={"state": "all", "sort": "created", "direction": "asc", "per_page": 1},
                timeout=30,
            )
            if response.status_code == 200:
                data = response.json()
                if data:
                    result["first_date"] = data[0].get("created_at")
        except Exception as e:
            logger.warning(f"Error fetching oldest GitHub PR: {e}")

        return result

    def _fetch_gitlab_date_range(self) -> dict:
        """Fetch date range from GitLab (oldest and newest MR)."""
        result = {"first_date": None, "last_date": None}

        project_id = self._get_gitlab_project_id()
        if not project_id:
            return result

        # Newest MR
        try:
            response = requests.get(
                f"{self.base_url}/projects/{project_id}/merge_requests",
                headers=self.headers,
                params={"state": "all", "order_by": "created_at", "sort": "desc", "per_page": 1},
                timeout=30,
                verify=self.verify_tls,
            )
            if response.status_code == 200:
                data = response.json()
                if data:
                    result["last_date"] = data[0].get("created_at")
        except Exception as e:
            logger.warning(f"Error fetching newest GitLab MR: {e}")

        # Oldest MR
        try:
            response = requests.get(
                f"{self.base_url}/projects/{project_id}/merge_requests",
                headers=self.headers,
                params={"state": "all", "order_by": "created_at", "sort": "asc", "per_page": 1},
                timeout=30,
                verify=self.verify_tls,
            )
            if response.status_code == 200:
                data = response.json()
                if data:
                    result["first_date"] = data[0].get("created_at")
        except Exception as e:
            logger.warning(f"Error fetching oldest GitLab MR: {e}")

        return result
