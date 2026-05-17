"""Backward-compatibility shim.

Canonical location: ``collectors.domain.processors.metadata_extractor``.
"""
from collectors.domain.processors.metadata_extractor import (  # noqa: F401
    _ReplayStream,
    extract_cleaning_metadata,
)

__all__ = ["extract_cleaning_metadata", "_ReplayStream"]
