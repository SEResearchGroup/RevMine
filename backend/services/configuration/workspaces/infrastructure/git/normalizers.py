"""Repository data normalizers for GitHub and GitLab API responses.

Infrastructure layer: transforms raw API payloads into a uniform internal
representation consumed by the service layer.  Each normalizer exposes two
views of the same data:

- ``normalize``       — lightweight dict for API list responses
- ``normalize_for_db`` — full dict ready for ``Repository.objects.update_or_create``
"""
from datetime import datetime
from typing import Dict, List, Optional


class BaseNormalizer:
    """Abstract base for platform-specific repository normalizers."""

    @staticmethod
    def parse_datetime(dt_string: Optional[str]) -> Optional[datetime]:
        """Parse an ISO 8601 datetime string, returning ``None`` on failure."""
        if not dt_string:
            return None
        try:
            return datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
        except Exception:
            return None

    def normalize(self, repo: Dict) -> Dict:
        """Return a lightweight dict for API listing."""
        raise NotImplementedError

    def normalize_for_db(self, repo: Dict) -> Dict:
        """Return a full dict suitable for database storage."""
        raise NotImplementedError


class GitHubNormalizer(BaseNormalizer):
    """Normalizes GitHub API repository payloads."""

    def normalize(self, repo: Dict) -> Dict:
        """Lightweight format for repository list."""
        return {
            "id": repo.get("id"),
            "name": repo.get("name"),
            "full_name": repo.get("full_name"),
            "description": repo.get("description"),
            "url": repo.get("html_url"),
            "clone_url": repo.get("clone_url"),
            "ssh_url": repo.get("ssh_url"),
            "default_branch": repo.get("default_branch", "main"),
            "private": repo.get("private", False),
            "language": repo.get("language"),
            "updated_at": repo.get("updated_at"),
            "visibility": "private" if repo.get("private") else "public",
        }

    def normalize_for_db(self, repo: Dict) -> Dict:
        """Full format for database storage."""
        owner = repo.get("owner", {})
        return {
            "external_id": str(repo["id"]),
            "name": repo["name"],
            "full_name": repo["full_name"],
            "description": repo.get("description"),
            "url": repo.get("url") or repo.get("clone_url"),
            "web_url": repo.get("html_url") or repo.get("url"),
            "owner": (
                owner.get("login")
                if isinstance(owner, dict)
                else repo.get("full_name", "").split("/")[0]
            ),
            "owner_type": (
                owner.get("type")
                if isinstance(owner, dict)
                else "User"
            ),
            "default_branch": repo.get("default_branch", "main"),
            "language": repo.get("language"),
            "stars_count": repo.get("stargazers_count", 0),
            "forks_count": repo.get("forks_count", 0),
            "open_issues_count": repo.get("open_issues_count", 0),
            "is_private": repo.get("private", False),
            "is_fork": repo.get("fork", False),
            "is_archived": repo.get("archived", False),
            "created_at_platform": self.parse_datetime(
                repo.get("created_at") or repo.get("updated_at")
            ),
            "last_activity_at": self.parse_datetime(repo.get("updated_at")),
            "raw_data": repo,
        }


class GitLabNormalizer(BaseNormalizer):
    """Normalizes GitLab API repository payloads."""

    def normalize(self, repo: Dict) -> Dict:
        """Lightweight format for repository list."""
        return {
            "id": repo.get("id"),
            "name": repo.get("name"),
            "full_name": repo.get("path_with_namespace"),
            "description": repo.get("description"),
            "web_url": repo.get("web_url"),
            "url": repo.get("http_url_to_repo"),
            "clone_url": repo.get("http_url_to_repo"),
            "ssh_url": repo.get("ssh_url_to_repo"),
            "default_branch": repo.get("default_branch", "main"),
            "private": repo.get("visibility") in ["private", "internal"],
            "language": None,
            "updated_at": repo.get("last_activity_at"),
            "visibility": repo.get("visibility", "private"),
            "created_at": repo.get("created_at"),
        }

    def normalize_for_db(self, repo: Dict) -> Dict:
        """Full format for database storage."""
        namespace = repo.get("namespace", {})
        return {
            "external_id": str(repo["id"]),
            "name": repo["name"],
            "full_name": repo.get("path_with_namespace") or repo.get("full_name"),
            "description": repo.get("description"),
            "url": (
                repo.get("http_url_to_repo")
                or repo.get("url")
                or repo.get("clone_url")
            ),
            "web_url": repo.get("web_url"),
            "owner": (
                namespace.get("full_path")
                if isinstance(namespace, dict)
                else repo.get("full_name", "").split("/")[0]
            ),
            "owner_type": (
                namespace.get("kind")
                if isinstance(namespace, dict)
                else "user"
            ),
            "default_branch": repo.get("default_branch", "main"),
            "language": None,
            "stars_count": repo.get("star_count", 0),
            "forks_count": repo.get("forks_count", 0),
            "open_issues_count": repo.get("open_issues_count", 0),
            "is_private": (
                repo.get("visibility") == "private" or repo.get("private", False)
            ),
            "is_fork": "forked_from_project" in repo,
            "is_archived": repo.get("archived", False),
            "created_at_platform": self.parse_datetime(repo.get("created_at")),
            "last_activity_at": self.parse_datetime(
                repo.get("last_activity_at") or repo.get("updated_at")
            ),
            "raw_data": repo,
        }


def get_normalizer(platform: str) -> BaseNormalizer:
    """Factory: return the appropriate normalizer for *platform*."""
    return GitHubNormalizer() if platform == "github" else GitLabNormalizer()
