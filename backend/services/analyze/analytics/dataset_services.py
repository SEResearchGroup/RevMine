# Backward-compatibility shim — do not add logic here.
from analytics.services.dataset_service import DatasetService  # noqa: F401
__all__ = ["DatasetService"]
