# Backward-compatibility shim — do not add logic here.
from analytics.infrastructure.tasks.devops_tasks import (  # noqa: F401
    start_job,
)
__all__ = ["start_job"]
