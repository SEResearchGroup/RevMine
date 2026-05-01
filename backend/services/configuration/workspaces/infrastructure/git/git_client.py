"""Unified Git API HTTP client.

Infrastructure layer: manages raw HTTP communication with GitHub and GitLab.
No business logic here — only request construction and response forwarding.
"""
from typing import Dict, Optional

import requests


class GitAPIClient:
    """Unified client to interact with Git APIs (GitHub, GitLab).

    Responsibility: manage HTTP requests and API configuration.
    """

    GITHUB_API = "https://api.github.com"
    GITLAB_API = "https://gitlab.com/api/v4"

    def __init__(self, platform: str, token: str, url: Optional[str] = None):
        self.platform = platform
        self.token = token
        self.url = url
        self._api_url: Optional[str] = None
        self._headers: Optional[Dict[str, str]] = None

    @property
    def api_url(self) -> str:
        """Build the API base URL based on the platform."""
        if self._api_url:
            return self._api_url

        if self.platform == "github":
            self._api_url = self.GITHUB_API
        elif self.platform == "gitlab":
            self._api_url = self.GITLAB_API
        else:  # gitlab_self
            if not self.url:
                raise ValueError("URL required for GitLab self-hosted")
            self._api_url = self.url.rstrip("/") + "/api/v4"

        return self._api_url

    @property
    def headers(self) -> Dict[str, str]:
        """Build authentication headers based on the platform."""
        if self._headers:
            return self._headers

        if self.platform == "github":
            self._headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json",
            }
        elif self.platform == "gitlab":
            self._headers = {"PRIVATE-TOKEN": self.token}
        else:
            self._headers = {"Authorization": f"Bearer {self.token}"}

        return self._headers

    def get(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        timeout: int = 15,
    ) -> requests.Response:
        """Perform a GET request to the Git API.

        Args:
            endpoint: The endpoint path (e.g. ``/user``, ``/projects``)
            params: Optional query-string parameters
            timeout: Timeout in seconds

        Returns:
            ``requests.Response`` object

        Raises:
            requests.RequestException: On network errors
        """
        url = f"{self.api_url}{endpoint}"
        return requests.get(url, headers=self.headers, params=params, timeout=timeout)
