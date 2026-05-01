"""Data processors — streaming metadata extraction."""
from collectors.domain.processors.metadata_extractor import (
    extract_cleaning_metadata,
    _ReplayStream,
)

__all__ = ["extract_cleaning_metadata", "_ReplayStream"]
