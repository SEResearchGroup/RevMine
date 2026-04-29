"""Workspace application service.

Orchestrates workspace lifecycle operations: creation, validation, and update.
Coordinates domain rules, infrastructure (connection testing), and persistence.
"""
from typing import Dict, Optional, Tuple

from workspaces.domain.rules import workspace_rules
from workspaces.infrastructure.git.connection_service import ConnectionService
from workspaces.models import Workspace


class WorkspaceService:
    """Application service for workspace lifecycle management."""

    @staticmethod
    def create_workspace(
        user_id: int, validated_data: Dict
    ) -> Tuple[Workspace, Dict]:
        """Create a workspace after validating the Git connection.

        Enforces business rules (unique name, valid platform / URL), tests
        connectivity, then persists the workspace with an encrypted token.

        Args:
            user_id:        Authenticated user identifier
            validated_data: Deserialised request data.  **Mutated**: ``token``
                            is popped from the dict before saving.

        Returns:
            Tuple of (created :class:`~workspaces.models.Workspace`,
            connection test result dict).

        Raises:
            ValueError: On duplicate name, unsupported platform, missing URL,
                        or failed connection test.
        """
        platform = validated_data["platform"]
        token = validated_data.pop("token")
        url = validated_data.get("url")
        name = validated_data.get("name")

        workspace_rules.check_name_unique(user_id, name)
        workspace_rules.validate_platform(platform)
        workspace_rules.validate_url_requirement(platform, url)

        connection_result = ConnectionService.test_connection(platform, token, url)
        if not connection_result["success"]:
            raise ValueError(connection_result["message"])

        workspace = Workspace(user=user_id, **validated_data)
        workspace.set_token(token)
        workspace.save()

        return workspace, connection_result

    @staticmethod
    def update_workspace(
        workspace: Workspace,
        validated_data: Dict,
        token: Optional[str] = None,
    ) -> Workspace:
        """Update workspace fields, re-testing connectivity when the token changes.

        Args:
            workspace:      Existing :class:`~workspaces.models.Workspace` instance
            validated_data: Partial or full field updates
            token:          New plaintext token, or ``None`` to leave it unchanged

        Returns:
            Updated :class:`~workspaces.models.Workspace` instance

        Raises:
            ValueError: If a new token fails the connection test
        """
        if token is not None:
            platform = validated_data.get("platform", workspace.platform)
            url = validated_data.get("url", workspace.url)
            connection_result = ConnectionService.test_connection(platform, token, url)
            if not connection_result["success"]:
                raise ValueError(connection_result["message"])

        for key, value in validated_data.items():
            setattr(workspace, key, value)
        workspace.save()

        if token is not None:
            workspace.set_token(token)
            workspace.save()

        return workspace
