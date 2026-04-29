# SHIM: content moved to workspaces.api.schema — re-exported for backward compatibility.
from workspaces.api.schema import (
    workspace_list_schema,
    workspace_create_schema,
    workspace_detail_retrieve_schema,
    workspace_update_put_schema,
    workspace_update_patch_schema,
    workspace_delete_schema,
    workspace_token_schema,
    workspace_test_connection_schema,
    workspace_repositories_schema,
    repository_import_schema,
    repository_list_schema,
    repository_detail_schema,
    repository_partial_update_schema,
    repository_delete_schema,
)

__all__ = [
    "workspace_list_schema",
    "workspace_create_schema",
    "workspace_detail_retrieve_schema",
    "workspace_update_put_schema",
    "workspace_update_patch_schema",
    "workspace_delete_schema",
    "workspace_token_schema",
    "workspace_test_connection_schema",
    "workspace_repositories_schema",
    "repository_import_schema",
    "repository_list_schema",
    "repository_detail_schema",
    "repository_partial_update_schema",
    "repository_delete_schema",
]
