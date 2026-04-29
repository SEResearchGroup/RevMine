"""Unit tests for workspace business rules (domain layer)."""
import pytest

from workspaces.domain.rules.workspace_rules import (
    validate_platform,
    validate_url_requirement,
    check_name_unique,
)


class TestValidatePlatform:
    def test_github_is_valid(self):
        validate_platform("github")  # no exception

    def test_gitlab_is_valid(self):
        validate_platform("gitlab")

    def test_gitlab_self_is_valid(self):
        validate_platform("gitlab_self")

    def test_unknown_platform_raises(self):
        with pytest.raises(ValueError, match="Unsupported platform"):
            validate_platform("bitbucket")

    def test_empty_platform_raises(self):
        with pytest.raises(ValueError):
            validate_platform("")


class TestValidateUrlRequirement:
    def test_gitlab_self_with_url_is_valid(self):
        validate_url_requirement("gitlab_self", "https://gitlab.company.com")

    def test_gitlab_self_without_url_raises(self):
        with pytest.raises(ValueError, match="URL is required"):
            validate_url_requirement("gitlab_self", None)

    def test_gitlab_self_empty_url_raises(self):
        with pytest.raises(ValueError, match="URL is required"):
            validate_url_requirement("gitlab_self", "")

    def test_github_without_url_is_valid(self):
        validate_url_requirement("github", None)  # GitHub never needs a URL

    def test_gitlab_without_url_is_valid(self):
        validate_url_requirement("gitlab", None)


@pytest.mark.django_db
class TestCheckNameUnique:
    """These tests require a database to check for existing workspaces."""

    def test_new_name_passes(self):
        # No workspace with this name exists ⇒ should not raise
        check_name_unique(user_id=1, name="Unique Workspace")

    def test_duplicate_name_raises(self, create_workspace):
        ws = create_workspace(user_id=1, name="My Workspace")
        with pytest.raises(ValueError, match="already exists"):
            check_name_unique(user_id=1, name="My Workspace")

    def test_same_name_different_user_is_valid(self, create_workspace):
        create_workspace(user_id=1, name="Shared Name")
        check_name_unique(user_id=2, name="Shared Name")  # different user — OK

    def test_exclude_own_id_allows_update(self, create_workspace):
        ws = create_workspace(user_id=1, name="My Workspace")
        # Updating a workspace should be allowed to keep its own name
        check_name_unique(user_id=1, name="My Workspace", exclude_id=ws.id)
