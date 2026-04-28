# Backward-compatibility shim — do not add logic here.
from analytics.infrastructure.tasks.celery_tasks import (  # noqa: F401
    process_analysis,
    process_batch,
    cleanup_old_analyses,
)
__all__ = ["process_analysis", "process_batch", "cleanup_old_analyses"]
