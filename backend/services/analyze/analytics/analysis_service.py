# Backward-compatibility shim — do not add logic here.
from analytics.services.analysis_service import AnalysisService  # noqa: F401
__all__ = ["AnalysisService"]
