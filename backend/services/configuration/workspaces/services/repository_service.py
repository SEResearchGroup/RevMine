"""Repository application service.

Orchestrates repository import: resolves external IDs, fetches remote data,
normalises payloads, and persists ``Repository`` records.
"""
from typing import Dict, List, Optional, Tuple

from django.utils import timezone

from workspaces.infrastructure.git.normalizers import get_normalizer
from workspaces.infrastructure.git.repository_fetcher import RepositoryFetcher
from workspaces.models import Repository, Workspace


class RepositoryService:
    """Application service for repository import and management."""

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @staticmethod
    def fetch_repositories(
        platform: str, token: str, url: Optional[str] = None
    ) -> Dict:
        """Fetch all accessible repositories for the authenticated user.

        Delegates to :class:`~workspaces.infrastructure.git.repository_fetcher.RepositoryFetcher`.
        Kept here for backward compatibility with callers that reference
        ``RepositoryService.fetch_repositories``.
        """
        return RepositoryFetcher.fetch_all(platform, token, url)

    @staticmethod
    def fetch_repository_by_id(
        platform: str,
        token: str,
        repository_id: str,
        url: Optional[str] = None,
    ) -> Dict:
        """Fetch a single repository by external platform ID.

        Delegates to :meth:`RepositoryFetcher.fetch_by_id`.
        Kept here for backward compatibility.
        """
        return RepositoryFetcher.fetch_by_id(platform, token, repository_id, url)

    @staticmethod
    def import_repositories(
        workspace: Workspace,
        repository_ids: List[str],
    ) -> Tuple[List[Repository], List[Dict]]:
        """Import selected repositories into the database.

        Resolves each requested ID against the workspace's repository listing;
        falls back to a direct single-repo fetch for IDs not in the listing
        (e.g. public repos supplied by external ID).

        Args:
            workspace:       Target :class:`~workspaces.models.Workspace`
            repository_ids:  External platform IDs to import

        Returns:
            Tuple of (successfully imported repositories, per-repo error dicts).

        Raises:
            Exception:   If the initial repository listing fails entirely.
            ValueError:  If no valid repositories could be resolved.
        """
        # Deduplicate and sanitise IDs
        normalised_ids: List[str] = list(
            {str(rid).strip() for rid in repository_ids if str(rid).strip()}
        )

        # Fetch the workspace's full repository listing once
        fetch_result = RepositoryService.fetch_repositories(
            workspace.platform, workspace.get_token(), workspace.url
        )
        if not fetch_result["success"]:
            raise Exception(fetch_result["message"])

        repos_by_id: Dict[str, Dict] = {
            str(repo.get("id")): repo
            for repo in fetch_result["repositories"]
            if repo.get("id") is not None
        }

        selected: List[Dict] = []
        missing_ids: List[str] = []

        for rid in normalised_ids:
            if rid in repos_by_id:
                selected.append(repos_by_id[rid])
            else:
                missing_ids.append(rid)

        # Fall back to direct lookup for IDs not in the listing
        errors: List[Dict] = []
        for rid in missing_ids:
            result = RepositoryService.fetch_repository_by_id(
                workspace.platform, workspace.get_token(), rid, workspace.url
            )
            if result["success"] and result.get("repository"):
                selected.append(result["repository"])
            else:
                errors.append({"repository": rid, "error": result["message"]})

        if not selected:
            if errors:
                raise ValueError(errors[0]["error"])
            raise ValueError("No repositories found with provided IDs")

        # Persist each selected repository
        normalizer = get_normalizer(workspace.platform)
        imported: List[Repository] = []
        for repo_data in selected:
            try:
                repo = RepositoryService._import_single(workspace, repo_data, normalizer)
                imported.append(repo)
            except Exception as exc:
                label = (
                    repo_data.get("name")
                    or repo_data.get("full_name")
                    or repo_data.get("id")
                )
                errors.append({"repository": label, "error": str(exc)})

        workspace.last_sync = timezone.now()
        workspace.save()

        return imported, errors

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _import_single(
        workspace: Workspace,
        repo_data: Dict,
        normalizer=None,
    ) -> Repository:
        """Upsert a single repository record in the database."""
        if normalizer is None:
            normalizer = get_normalizer(workspace.platform)
        normalised = normalizer.normalize_for_db(repo_data)
        repository, _ = Repository.objects.update_or_create(
            workspace=workspace,
            external_id=normalised["external_id"],
            defaults=normalised,
        )
        return repository

    # ------------------------------------------------------------------
    # Backward-compatibility helpers (used by legacy code / shim layer)
    # ------------------------------------------------------------------

    @staticmethod
    def _get_normalizer(platform: str):
        return get_normalizer(platform)

    @staticmethod
    def _get_list_params(platform: str) -> Dict:
        return RepositoryFetcher._list_params(platform)

    @staticmethod
    def _normalize_all(repos_data: List[Dict], platform: str) -> List[Dict]:
        normalizer = get_normalizer(platform)
        return [normalizer.normalize(r) for r in repos_data]
