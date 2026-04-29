"""Workspace business rules.

Pure domain logic: validates workspace invariants.
No I/O, no framework dependencies (Django model imported lazily inside
functions to avoid circular imports at module load time).
"""
from typing import Optional


VALID_PLATFORMS = frozenset({"github", "gitlab", "gitlab_self"})


def validate_platform(platform: str) -> None:
    """Raise ``ValueError`` if *platform* is not one of the supported values."""
    if platform not in VALID_PLATFORMS:
        raise ValueError(
            f"Unsupported platform '{platform}'. "
            f"Must be one of {sorted(VALID_PLATFORMS)}"
        )


def validate_url_requirement(platform: str, url: Optional[str]) -> None:
    """Raise ``ValueError`` if a GitLab self-hosted workspace is missing its URL."""
    if platform == "gitlab_self" and not url:
        raise ValueError("URL is required for GitLab self-hosted")


def check_name_unique(
    user_id: int, name: str, exclude_id: Optional[int] = None
) -> None:
    """Raise ``ValueError`` if a workspace with *name* already exists for *user_id*.

    Args:
        user_id:    Owner of the workspace
        name:       Desired workspace name
        exclude_id: When updating, exclude the workspace being edited so that
                    keeping the same name does not trigger the uniqueness check.
    """
    from workspaces.models import Workspace  # lazy import to avoid circular deps

    qs = Workspace.objects.filter(user=user_id, name=name)
    if exclude_id is not None:
        qs = qs.exclude(id=exclude_id)
    if qs.exists():
        raise ValueError(f"A workspace named '{name}' already exists")
