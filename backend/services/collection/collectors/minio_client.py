"""Backward-compatibility shim.

Canonical location: ``collectors.infrastructure.storage.minio_client``
"""
from collectors.infrastructure.storage.minio_client import MinIOClient  # noqa: F401

__all__ = ["MinIOClient"]
