"""Remote repository fetcher.

Infrastructure layer: fetches repository listings and individual repos from
GitHub / GitLab APIs.  No database operations — pure I/O.
"""
from typing import Dict, List, Optional
from urllib.parse import quote

import requests

from .git_client import GitAPIClient
from .normalizers import get_normalizer


class RepositoryFetcher:
    """Fetches repository data from remote Git platform APIs."""

    @staticmethod
    def fetch_all(
        platform: str, token: str, url: Optional[str] = None
    ) -> Dict:
        """Fetch all accessible repositories for the authenticated user.

        Returns:
            Dict with ``success``, ``message``, and ``repositories``
            (list of normalised lightweight dicts).
        """
        try:
            client = GitAPIClient(platform, token, url)
            params = RepositoryFetcher._list_params(platform)
            endpoint = "/user/repos" if platform == "github" else "/projects"
            response = client.get(endpoint, params=params)

            if response.status_code == 200:
                normalizer = get_normalizer(platform)
                repos = [normalizer.normalize(r) for r in response.json()]
                return {
                    "success": True,
                    "message": f"{len(repos)} repositories found",
                    "repositories": repos,
                }
            elif response.status_code == 401:
                return {
                    "success": False,
                    "message": "Invalid or expired token",
                    "repositories": [],
                }
            else:
                return {
                    "success": False,
                    "message": f"API error: {response.status_code}",
                    "repositories": [],
                }

        except ValueError as e:
            return {"success": False, "message": str(e), "repositories": []}
        except requests.Timeout:
            return {
                "success": False,
                "message": "Timeout: server not responding",
                "repositories": [],
            }
        except requests.RequestException as e:
            return {
                "success": False,
                "message": f"Connection error: {str(e)}",
                "repositories": [],
            }

    @staticmethod
    def fetch_by_id(
        platform: str,
        token: str,
        repository_id: str,
        url: Optional[str] = None,
    ) -> Dict:
        """Fetch a single repository by its external platform ID.

        Used as a fallback when the repository is not in the workspace's
        default listing (e.g. a public repository supplied by external ID).

        Returns:
            Dict with ``success``, ``message``, and ``repository``
            (raw API payload or ``None``).
        """
        try:
            client = GitAPIClient(platform, token, url)
            endpoint = (
                f"/repositories/{repository_id}"
                if platform == "github"
                else f"/projects/{quote(str(repository_id), safe='')}"
            )
            response = client.get(endpoint)

            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "Repository found",
                    "repository": response.json(),
                }
            elif response.status_code == 401:
                return {
                    "success": False,
                    "message": "Invalid or expired token",
                    "repository": None,
                }
            elif response.status_code in (403, 404):
                return {
                    "success": False,
                    "message": "Repository not found or inaccessible",
                    "repository": None,
                }
            else:
                return {
                    "success": False,
                    "message": f"API error: {response.status_code}",
                    "repository": None,
                }

        except ValueError as e:
            return {"success": False, "message": str(e), "repository": None}
        except requests.Timeout:
            return {
                "success": False,
                "message": "Timeout: server not responding",
                "repository": None,
            }
        except requests.RequestException as e:
            return {
                "success": False,
                "message": f"Connection error: {str(e)}",
                "repository": None,
            }

    @staticmethod
    def _list_params(platform: str) -> Dict:
        """Return platform-optimal query parameters for listing repositories."""
        if platform == "github":
            return {
                "per_page": 100,
                "sort": "updated",
                "affiliation": "owner,collaborator,organization_member",
            }
        return {"per_page": 100, "order_by": "updated_at", "membership": True}
