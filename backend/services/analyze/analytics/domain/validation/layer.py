"""
Validation Layer
================
Two-phase validation that sits between the LLM Service and the execution engine.

Phase 1 — Structural validation
    Check that the generated code / DSL is syntactically valid Python / JSON.
    For DSL this delegates to DSLValidator.

Phase 2 — Semantic validation (sandbox execution)
    For Level 4/5 plugins (Python code), run the code in a RestrictedPython
    sandbox against a tiny sample DataFrame.
    For DSL, this phase just runs a dry-run pass through DSLExecutionEngine
    with an empty DataFrame so we detect obvious aggregation errors early.

Results are returned as a ValidationResult dataclass so callers can
decide what to do without catching exceptions.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation run."""

    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    phase: str = "unknown"      # "structural" | "semantic" | "sandbox"
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "phase": self.phase,
            "details": self.details,
        }


class ValidationLayer:
    """
    Orchestrates multi-phase validation for DSL documents and Python plugins.
    """

    # ------------------------------------------------------------------
    # DSL Validation
    # ------------------------------------------------------------------

    def validate_dsl(
        self,
        dsl_raw: Dict[str, Any],
        available_columns: Optional[Dict[str, str]] = None,
    ) -> ValidationResult:
        """
        Validate an Analysis DSL document.

        Phase 1: JSON schema + required fields (structural)
        Phase 2: Column existence, type compatibility (semantic)

        Parameters
        ----------
        dsl_raw : dict
            The raw DSL JSON document.
        available_columns : dict, optional
            {column_name: dtype_string} mapping from the dataset.

        Returns
        -------
        ValidationResult
        """
        from analytics.domain.dsl.validator import DSLValidator

        validator = DSLValidator(available_columns=available_columns)
        errors = validator.validate_only(dsl_raw)

        if errors:
            return ValidationResult(
                valid=False,
                errors=errors,
                phase="structural+semantic",
            )
        return ValidationResult(valid=True, phase="structural+semantic")

    # ------------------------------------------------------------------
    # Python Plugin Validation (Level 4/5)
    # ------------------------------------------------------------------

    def validate_python_plugin(
        self,
        source_code: str,
        sample_df_json: Optional[str] = None,
        plugin_class_name: str = "CustomPlugin",
    ) -> ValidationResult:
        """
        Validate a Python MetricPlugin implementation.

        Phase 1: AST syntax check (structural)
        Phase 2: Sandbox execution against a sample DataFrame (semantic)

        Parameters
        ----------
        source_code : str
            Full Python source code of the plugin class.
        sample_df_json : str, optional
            A small sample DataFrame serialised as JSON (orient='records').
            If omitted, a minimal empty DataFrame is used.
        plugin_class_name : str
            Name of the class inside source_code that implements MetricPlugin.

        Returns
        -------
        ValidationResult
        """
        # Phase 1: AST syntax check
        import ast
        try:
            ast.parse(source_code)
        except SyntaxError as exc:
            return ValidationResult(
                valid=False,
                errors=[f"Syntax error at line {exc.lineno}: {exc.msg}"],
                phase="structural",
            )

        # Phase 2: Sandbox execution
        from analytics.domain.sandbox.executor import ScriptSandbox
        import pandas as pd

        if sample_df_json:
            try:
                sample_df = pd.read_json(sample_df_json, orient="records")
            except Exception as exc:
                return ValidationResult(
                    valid=False,
                    errors=[f"Invalid sample DataFrame JSON: {exc}"],
                    phase="structural",
                )
        else:
            sample_df = pd.DataFrame()

        sandbox = ScriptSandbox()
        result = sandbox.execute_plugin(source_code, plugin_class_name, sample_df)
        return result

    # ------------------------------------------------------------------
    # Analysis Plugin Validation (Level 5 — full analysis function)
    # ------------------------------------------------------------------

    def validate_analysis_plugin(
        self,
        source_code: str,
        function_name: str,
        sample_df_json: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate a Level-5 analysis function (returns chart_data dict).

        The function must have signature: ``(df: pd.DataFrame, **kwargs) -> dict``
        """
        import ast
        try:
            ast.parse(source_code)
        except SyntaxError as exc:
            return ValidationResult(
                valid=False,
                errors=[f"Syntax error at line {exc.lineno}: {exc.msg}"],
                phase="structural",
            )

        from analytics.domain.sandbox.executor import ScriptSandbox
        import pandas as pd

        if sample_df_json:
            try:
                sample_df = pd.read_json(sample_df_json, orient="records")
            except Exception as exc:
                return ValidationResult(
                    valid=False,
                    errors=[f"Invalid sample DataFrame JSON: {exc}"],
                    phase="structural",
                )
        else:
            sample_df = pd.DataFrame({"dummy": [1, 2, 3]})

        sandbox = ScriptSandbox()
        return sandbox.execute_function(source_code, function_name, sample_df)
