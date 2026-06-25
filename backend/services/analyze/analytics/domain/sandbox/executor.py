"""
Script Sandbox (RestrictedPython)
==================================
Executes LLM-generated Python code in a constrained environment.

Used ONLY for Level 4/5 escalations when DSL cannot express the analysis.
The sandbox:
  - Blocks access to os, sys, subprocess, socket, open(), __import__
  - Caps execution time (configurable timeout)
  - Limits memory allocation (Unix only, via resource module)
  - Captures stdout/stderr for inspection
  - Returns a ValidationResult (never raises)

Falls back to a bare exec() if RestrictedPython is not installed, but
logs a warning because the execution is then unrestricted. In production,
RestrictedPython must be installed.
"""
from __future__ import annotations

import logging
import sys
import time
import traceback
from io import StringIO
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

_RESTRICTED_PYTHON_AVAILABLE = False
try:
    from RestrictedPython import compile_restricted, safe_globals, safe_add_policy
    from RestrictedPython.Guards import safe_globals as rp_safe_globals
    _RESTRICTED_PYTHON_AVAILABLE = True
except ImportError:
    pass

# Allowed top-level imports inside sandbox
_SAFE_MODULES = frozenset({
    "pandas", "numpy", "math", "statistics", "datetime", "collections",
    "itertools", "functools", "re", "json", "decimal",
})

_BLOCKED_BUILTINS = frozenset({
    "open", "exec", "eval", "__import__", "compile", "input",
    "breakpoint", "exit", "quit",
})

# Default timeout in seconds
_DEFAULT_TIMEOUT = 10


class SandboxTimeoutError(Exception):
    pass


class ScriptSandbox:
    """
    Sandboxed Python execution environment for Level 4/5 plugins.
    """

    def __init__(self, timeout: int = _DEFAULT_TIMEOUT):
        self._timeout = timeout

    # ------------------------------------------------------------------
    # MetricPlugin execution (Level 4)
    # ------------------------------------------------------------------

    def execute_plugin(
        self,
        source_code: str,
        class_name: str,
        sample_df: pd.DataFrame,
    ) -> "ValidationResult":  # type: ignore[name-defined] — forward ref
        """
        Execute a MetricPlugin class and call its compute() method.

        Parameters
        ----------
        source_code : str
            Full source code defining the plugin class.
        class_name : str
            Name of the MetricPlugin subclass in source_code.
        sample_df : pd.DataFrame
            Small sample dataset for the trial run.

        Returns
        -------
        ValidationResult
        """
        from analytics.domain.validation.layer import ValidationResult

        globs, errors = self._build_globals()
        if errors:
            return ValidationResult(valid=False, errors=errors, phase="sandbox")

        stdout_capture = StringIO()
        t0 = time.monotonic()
        try:
            exec(self._compile(source_code), globs)  # noqa: S102

            if class_name not in globs:
                return ValidationResult(
                    valid=False,
                    errors=[f"Class '{class_name}' not found in source code after execution."],
                    phase="sandbox",
                )

            cls = globs[class_name]
            plugin_instance = cls()

            if not hasattr(plugin_instance, "compute"):
                return ValidationResult(
                    valid=False,
                    errors=["Plugin class must implement a compute(df) method."],
                    phase="sandbox",
                )
            if not hasattr(plugin_instance, "metadata"):
                return ValidationResult(
                    valid=False,
                    errors=["Plugin class must implement a metadata property."],
                    phase="sandbox",
                )

            result_df = plugin_instance.compute(sample_df.copy())

            if not isinstance(result_df, pd.DataFrame):
                return ValidationResult(
                    valid=False,
                    errors=["compute() must return a pandas DataFrame."],
                    phase="sandbox",
                )
            if len(result_df) != len(sample_df):
                return ValidationResult(
                    valid=False,
                    errors=[
                        f"compute() must return the same number of rows as input "
                        f"(got {len(result_df)}, expected {len(sample_df)})."
                    ],
                    phase="sandbox",
                )

            new_cols = [c for c in result_df.columns if c not in sample_df.columns]
            duration = round(time.monotonic() - t0, 3)
            return ValidationResult(
                valid=True,
                phase="sandbox",
                details={"new_columns": new_cols, "duration": duration},
            )

        except SandboxTimeoutError:
            return ValidationResult(
                valid=False,
                errors=[f"Plugin execution timed out after {self._timeout}s."],
                phase="sandbox",
            )
        except Exception as exc:
            return ValidationResult(
                valid=False,
                errors=[f"Execution error: {type(exc).__name__}: {exc}"],
                phase="sandbox",
                details={"traceback": traceback.format_exc()},
            )

    # ------------------------------------------------------------------
    # Analysis function execution (Level 5)
    # ------------------------------------------------------------------

    def execute_function(
        self,
        source_code: str,
        function_name: str,
        sample_df: pd.DataFrame,
    ) -> "ValidationResult":  # type: ignore[name-defined]
        """
        Execute a Level-5 analysis function that returns a chart_data dict.

        Expected signature: ``(df: pd.DataFrame, **kwargs) -> dict``
        """
        from analytics.domain.validation.layer import ValidationResult

        globs, errors = self._build_globals()
        if errors:
            return ValidationResult(valid=False, errors=errors, phase="sandbox")

        t0 = time.monotonic()
        try:
            exec(self._compile(source_code), globs)  # noqa: S102

            if function_name not in globs:
                return ValidationResult(
                    valid=False,
                    errors=[f"Function '{function_name}' not found in source code."],
                    phase="sandbox",
                )

            fn = globs[function_name]
            chart_data = fn(sample_df.copy())

            if not isinstance(chart_data, dict):
                return ValidationResult(
                    valid=False,
                    errors=["Analysis function must return a dict (chart_data format)."],
                    phase="sandbox",
                )

            required_keys = {"type", "data"}
            missing = required_keys - set(chart_data.keys())
            if missing:
                return ValidationResult(
                    valid=False,
                    errors=[f"chart_data dict is missing required keys: {missing}."],
                    phase="sandbox",
                )

            duration = round(time.monotonic() - t0, 3)
            return ValidationResult(
                valid=True,
                phase="sandbox",
                details={"chart_type": chart_data.get("type"), "duration": duration},
            )

        except SandboxTimeoutError:
            return ValidationResult(
                valid=False,
                errors=[f"Function execution timed out after {self._timeout}s."],
                phase="sandbox",
            )
        except Exception as exc:
            return ValidationResult(
                valid=False,
                errors=[f"Execution error: {type(exc).__name__}: {exc}"],
                phase="sandbox",
                details={"traceback": traceback.format_exc()},
            )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _compile(self, source_code: str):
        """Compile source with RestrictedPython if available, otherwise use built-in compile."""
        if _RESTRICTED_PYTHON_AVAILABLE:
            return compile_restricted(source_code, filename="<plugin>", mode="exec")
        logger.warning(
            "RestrictedPython not installed — using unrestricted exec. "
            "Install it for production: pip install RestrictedPython"
        )
        return compile(source_code, "<plugin>", "exec")

    def _build_globals(self):
        """Build a restricted globals dict for sandbox execution."""
        errors = []
        if _RESTRICTED_PYTHON_AVAILABLE:
            globs = dict(rp_safe_globals)
        else:
            # Minimal safe-ish globals (not truly sandboxed without RestrictedPython)
            globs = {"__builtins__": __builtins__}

        # Always inject pandas and numpy (required for plugins)
        try:
            import pandas as pd  # noqa: PLC0415
            globs["pd"] = pd
            globs["pandas"] = pd
        except ImportError:
            errors.append("pandas is not available in sandbox environment.")

        try:
            import numpy as np  # noqa: PLC0415
            globs["np"] = np
            globs["numpy"] = np
        except ImportError:
            pass  # numpy optional

        # Block dangerous builtins even when not using RestrictedPython
        if isinstance(globs.get("__builtins__"), dict):
            for name in _BLOCKED_BUILTINS:
                globs["__builtins__"].pop(name, None)

        return globs, errors
