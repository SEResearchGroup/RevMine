from typing import Dict, List, Optional, Tuple
from datetime import datetime
import requests
from django.utils import timezone
from .models import Workspace, Repository


class GitAPIClient:
    """
    Unified client to interact with Git APIs (GitHub, GitLab).
    Responsibility: manage HTTP requests and API configuration.
    """

    GITHUB_API = "https://api.github.com"
    GITLAB_API = "https://gitlab.com/api/v4"

    def __init__(self, platform: str, token: str, url: Optional[str] = None):
        self.platform = platform
        self.token = token
        self.url = url
        self._api_url = None
        self._headers = None

    @property
    def api_url(self) -> str:
        """Build the API URL based on the platform."""
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
        elif self.platform == 'gitlab':
            self._headers = {'PRIVATE-TOKEN': self.token}
        else : 
            print(f"Using token for GitLab self-hosted: {self.token[:4]}...{self.token[-4:]}")
            self._headers = {'Authorization': f'Bearer {self.token}'}
           

        
        return self._headers

    def get(
        self, endpoint: str, params: Optional[Dict] = None, timeout: int = 15
    ) -> requests.Response:
        """
        Perform a GET request to the Git API.

        Args:
            endpoint: The endpoint path (e.g., '/user', '/projects')
            params: Optional query string parameters
            timeout: Timeout in seconds

        Returns:
            Response object from requests

        Raises:
            requests.RequestException: In case of network error
        """
        url = f"{self.api_url}{endpoint}"
        return requests.get(url, headers=self.headers, params=params, timeout=timeout)


class ConnectionService:
    """
    Service to test connections to Git APIs.
    Responsibility: validate credentials and connectivity.
    """

    @staticmethod
    def test_connection(platform: str, token: str, url: Optional[str] = None) -> Dict:
        """
        Test connection to a Git API.

        Args:
            platform: 'github', 'gitlab', or 'gitlab_self'
            token: Authentication token
            url: URL for GitLab self-hosted (optional)

        Returns:
            Dict with 'success', 'message', and optionally 'user_data'
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
        """
        Handle the HTTP response and return a standardized result.
        """
        if response.status_code == 200:
            return {
                "success": True,
                "message": "Connection successful",
                "user_data": response.json(),
            }
        elif response.status_code == 401:
            return {"success": False, "message": "Invalid or expired token"}
        else:
            return {"success": False, "message": f"API error: {response.status_code}"}


class RepositoryService:
    """
    Service to manage repository operations.
    Responsibility: fetch, normalize, and import repositories.
    """

    @staticmethod
    def fetch_repositories(
        platform: str, token: str, url: Optional[str] = None
    ) -> Dict:
        """
        Fetch the list of repositories from the Git API.

        Returns:
            Dict with 'success', 'message', 'repositories' (list)
        """
        try:
            client = GitAPIClient(platform, token, url)
            params = RepositoryService._get_list_params(platform)
            endpoint = "/user/repos" if platform == "github" else "/projects"

            response = client.get(endpoint, params=params)

            if response.status_code == 200:
                repos_data = response.json()
                repositories = RepositoryService._normalize_all(repos_data, platform)
                return {
                    "success": True,
                    "message": f"{len(repositories)} repositories found",
                    "repositories": repositories,
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
    def _get_list_params(platform: str) -> Dict:
        """Return optimal parameters based on the platform."""
        if platform == "github":
            return {
                "per_page": 100,
                "sort": "updated",
                "affiliation": "owner,collaborator,organization_member",
            }
        else:  # gitlab
            return {"per_page": 100, "order_by": "updated_at", "membership": True}

    @staticmethod
    def _normalize_all(repos_data: List[Dict], platform: str) -> List[Dict]:
        """Normalize a list of repositories."""
        normalizer = GitHubNormalizer() if platform == "github" else GitLabNormalizer()
        return [normalizer.normalize(repo) for repo in repos_data]

    @staticmethod
    def import_repositories(
        workspace: Workspace, repository_ids: List[str]
    ) -> Tuple[List[Repository], List[Dict]]:
        """
        Import selected repositories into the database.

        Args:
            workspace: Workspace instance
            repository_ids: List of external IDs to import

        Returns:
            Tuple (imported repositories, errors)
        """
        print(f"Importing repositories for workspace {workspace.id}...")
        result = RepositoryService.fetch_repositories(
            workspace.platform, workspace.get_token(), workspace.url
        )

        if not result["success"]:
            print(f"Failed to fetch repositories: {result['message']}")
            raise Exception(result["message"])

        # Filter the selected repositories

        all_repos = result["repositories"]
        selected = [
            repo
            for repo in all_repos
            if str(repo.get("id")) in [str(rid) for rid in repository_ids]
        ]

        print(f"Selected {len(selected)} repositories for import.")
        print(f"Repository IDs to import: {repository_ids}")
        if not selected:
            raise ValueError("No repositories found with provided IDs")

        # Import each repository
        imported = []
        errors = []
        for repo_data in selected:
            try:
                repo = RepositoryService._import_single(workspace, repo_data)
                print(f"Imported repository: {repo.full_name}")
                imported.append(repo)
            except Exception as e:
                print(f"Error importing repository {repo_data.get('name')}: {str(e)}")
                errors.append({"repository": repo_data.get("name"), "error": str(e)})

        # Update the sync date
        workspace.last_sync = timezone.now()
        workspace.save()

        return imported, errors

    @staticmethod
    def _import_single(workspace: Workspace, repo_data: Dict) -> Repository:
        """Import a single repository."""
        normalizer = (
            GitHubNormalizer() if workspace.platform == "github" else GitLabNormalizer()
        )

        normalized = normalizer.normalize_for_db(repo_data)
        print(f"Importing repository: {normalized['full_name']}")
        repository, created = Repository.objects.update_or_create(
            workspace=workspace,
            external_id=normalized["external_id"],
            defaults=normalized,
        )

        return repository


# NORMALIZERS - API      Transformation


class BaseNormalizer:
    """Base class for normalizing repository data."""

    @staticmethod
    def parse_datetime(dt_string: Optional[str]) -> Optional[datetime]:
        """Parse an ISO 8601 date."""
        if not dt_string:
            return None
        try:
            return datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
        except Exception:
            return None

    def normalize(self, repo: Dict) -> Dict:
        """Normalize for API display (lightweight format)."""
        raise NotImplementedError

    def normalize_for_db(self, repo: Dict) -> Dict:
        """Normalize for database storage (full format)."""
        raise NotImplementedError


# class GitHubNormalizer(BaseNormalizer):
#     """Normalize GitHub data."""

#     def normalize(self, repo: Dict) -> Dict:
#         """Lightweight format for repository list."""
#         return {
#             'id': repo.get('id'),
#             'name': repo.get('name'),
#             'full_name': repo.get('full_name'),
#             'description': repo.get('description'),
#             'url': repo.get('html_url'),
#             'clone_url': repo.get('clone_url'),
#             'ssh_url': repo.get('ssh_url'),
#             'default_branch': repo.get('default_branch', 'main'),
#             'private': repo.get('private', False),
#             'language': repo.get('language'),
#             'updated_at': repo.get('updated_at'),
#             'visibility': 'private' if repo.get('private') else 'public'
#         }

#     def normalize_for_db(self, repo: Dict) -> Dict:
#         """Full format for database storage."""
#         print(f"Normalizing GitHub repository for DB: {repo}")
#         return {
#             'external_id': str(repo['id']),
#             'name': repo['name'],
#             'full_name': repo['full_name'],
#             'description': repo.get('description'),
#             'url': repo['url'],
#             'web_url': repo['html_url'],
#             'owner': repo['owner']['login'],
#             'owner_type': repo['owner']['type'],
#             'default_branch': repo.get('default_branch', 'main'),
#             'language': repo.get('language'),
#             'stars_count': repo.get('stargazers_count', 0),
#             'forks_count': repo.get('forks_count', 0),
#             'open_issues_count': repo.get('open_issues_count', 0),
#             'is_private': repo.get('private', False),
#             'is_fork': repo.get('fork', False),
#             'is_archived': repo.get('archived', False),
#             'created_at_platform': self.parse_datetime(repo.get('updated_at')),
#             'last_activity_at': self.parse_datetime(repo.get('updated_at')),
#             'raw_data': repo,
#         }


# class GitLabNormalizer(BaseNormalizer):
#     """Normalize GitLab data."""

#     def normalize(self, repo: Dict) -> Dict:
#         """Lightweight format for repository list."""
#         print(f"Normalizing GitLab repository for API: {repo}")
#         return {
#             'id': repo.get('id'),
#             'name': repo.get('name'),
#             'full_name': repo.get('path_with_namespace'),
#             'description': repo.get('description'),
#             'web_url': repo.get('web_url'),
#             'url': repo.get('url'),
#             'clone_url': repo.get('http_url_to_repo'),
#             'ssh_url': repo.get('ssh_url_to_repo'),
#             'default_branch': repo.get('default_branch', 'main'),
#             'private': repo.get('visibility') in ['private', 'internal'],
#             'language': None,
#             'updated_at': repo.get('last_activity_at'),
#             'visibility': repo.get('visibility', 'private'),
#             'created_at': repo.get('created_at'),
#         }

#     def normalize_for_db(self, repo: Dict) -> Dict:
#         """Full format for database storage."""
#         return {
#             'external_id': str(repo['id']),
#             'name': repo['name'],
#             'full_name': repo['full_name'],
#             'description': repo.get('description'),
#             'url': repo['url'],
#             'web_url': repo['web_url'],
#             'owner': repo['namespace']['full_path'],
#             'owner_type': repo['namespace']['kind'],
#             'default_branch': repo.get('default_branch', 'main'),
#             'language': None,
#             'stars_count': repo.get('star_count', 0),
#             'forks_count': repo.get('forks_count', 0),
#             'open_issues_count': repo.get('open_issues_count', 0),
#             'is_private': repo.get('visibility') == 'private',
#             'is_fork': 'forked_from_project' in repo,
#             'is_archived': repo.get('archived', False),
#             'created_at_platform': self.parse_datetime(repo.get('created_at')),
#             'last_activity_at': self.parse_datetime(repo.get('last_activity_at')),
#             'raw_data': repo,
#         }


class GitHubNormalizer(BaseNormalizer):
    """Normalize GitHub data."""

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
        print(
            f"Normalizing GitHub repository for DB: {repo.get('name', repo.get('full_name'))}"
        )
        return {
            "external_id": str(repo["id"]),
            "name": repo["name"],
            "full_name": repo["full_name"],
            "description": repo.get("description"),
            "url": repo.get("url") or repo.get("clone_url"),
            "web_url": repo.get("html_url") or repo.get("url"),
            "owner": (
                repo.get("owner", {}).get("login")
                if isinstance(repo.get("owner"), dict)
                else repo.get("full_name", "").split("/")[0]
            ),
            "owner_type": (
                repo.get("owner", {}).get("type")
                if isinstance(repo.get("owner"), dict)
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
    """Normalize GitLab data."""

    def normalize(self, repo: Dict) -> Dict:
        """Lightweight format for repository list."""
        print(
            f"Normalizing GitLab repository for API: {repo.get('name', repo.get('path_with_namespace'))}"
        )
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
        print(
            f"Normalizing GitLab repository for DB: {repo.get('name', repo.get('path_with_namespace'))}"
        )
        return {
            "external_id": str(repo["id"]),
            "name": repo["name"],
            "full_name": repo.get("path_with_namespace") or repo.get("full_name"),
            "description": repo.get("description"),
            "url": repo.get("http_url_to_repo")
            or repo.get("url")
            or repo.get("clone_url"),
            "web_url": repo.get("web_url"),
            "owner": (
                repo.get("namespace", {}).get("full_path")
                if isinstance(repo.get("namespace"), dict)
                else repo.get("full_name", "").split("/")[0]
            ),
            "owner_type": (
                repo.get("namespace", {}).get("kind")
                if isinstance(repo.get("namespace"), dict)
                else "user"
            ),
            "default_branch": repo.get("default_branch", "main"),
            "language": None,
            "stars_count": repo.get("star_count", 0),
            "forks_count": repo.get("forks_count", 0),
            "open_issues_count": repo.get("open_issues_count", 0),
            "is_private": repo.get("visibility") == "private"
            or repo.get("private", False),
            "is_fork": "forked_from_project" in repo,
            "is_archived": repo.get("archived", False),
            "created_at_platform": self.parse_datetime(repo.get("created_at")),
            "last_activity_at": self.parse_datetime(
                repo.get("last_activity_at") or repo.get("updated_at")
            ),
            "raw_data": repo,
        }


# WORKSPACE SERVICE - Workspace Management


class WorkspaceService:
    """
    Service to manage workspace operations.
    Responsibility: creation, validation, and management of workspaces.
    """

    @staticmethod
    def create_workspace(user_id: str, validated_data: Dict) -> Tuple[Workspace, Dict]:
        """
        Create a workspace after connection validation.

        Returns:
            Tuple (created workspace, connection test result)
            
        Raises:
            ValueError: If connection test fails or workspace name already exists
        """
        platform = validated_data['platform']
        token = validated_data.pop('token')
        url = validated_data.get('url')
        name = validated_data.get('name')
        
        # Check for duplicate workspace name
        if Workspace.objects.filter(user=user_id, name=name).exists():
            raise ValueError(f"A workspace named '{name}' already exists")
        
        # Connection test
        connection_result = ConnectionService.test_connection(platform, token, url)

        if not connection_result["success"]:
            raise ValueError(connection_result["message"])

        # Workspace creation
        workspace = Workspace(user=user_id, **validated_data)
        workspace.set_token(token)
        workspace.save()

        return workspace, connection_result

    @staticmethod
    def update_workspace(
        workspace: Workspace, validated_data: Dict, token: Optional[str] = None
    ) -> Workspace:
        """
        Update a workspace with optional token validation.
        """
        if token is not None:
            platform = validated_data.get("platform", workspace.platform)
            url = validated_data.get("url", workspace.url)

            connection_result = ConnectionService.test_connection(platform, token, url)

            if not connection_result["success"]:
                raise ValueError(connection_result["message"])

        # Update fields
        for key, value in validated_data.items():
            setattr(workspace, key, value)

        workspace.save()

        if token is not None:
            workspace.set_token(token)
            workspace.save()

        return workspace
