"""Git API connection testing service.

Infrastructure layer: validates credentials and connectivity against remote
Git hosting platforms.  Owns no business state — pure I/O.
"""
from typing import Dict, Optional

import requests

from .git_client import GitAPIClient


class ConnectionService:
    """Tests connectivity and authentication to Git platforms."""

    @staticmethod
    def test_connection(
        platform: str, token: str, url: Optional[str] = None
    ) -> Dict:
        """Test a connection to a Git API.

        Args:
            platform: ``'github'``, ``'gitlab'``, or ``'gitlab_self'``
            token:    Authentication token
            url:      Required only when *platform* is ``'gitlab_self'``

        Returns:
            Dict with ``success`` (bool), ``message`` (str), and optionally
            ``user_data`` (dict) on success.
        """
        try:
            client = GitAPIClient(platform, token, url)
            response = client.get("/user", timeout=10)
            return ConnectionService._handle_response(response)
        except ValueError as e:
            return {"success": False, "message": str(e)}
        except requests.Timeout:
            return {"success": False, "message": "Timeout: server not responding"}
        except requests.RequestException as e:
            return {"success": False, "message": f"Connection error: {str(e)}"}

    @staticmethod
    def _handle_response(response: requests.Response) -> Dict:
        """Map an HTTP response to a standardised result dict."""
        if response.status_code == 200:
            return {
                "success": True,
                "message": "Connection successful",
                "user_data": response.json(),
            }
        elif response.status_code == 401:
            return {"success": False, "message": "Invalid or expired token"}
        else:
            return {
                "success": False,
                "message": f"API error: {response.status_code}",
            }
