from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


CUSTOM_FORMULA_METRIC_CODE = "custom_formula"

ALLOWED_AGGREGATIONS = {"sum", "mean", "median", "count", "min", "max", "std"}
ALLOWED_SCOPES = {"mr", "time", "category"}
ALLOWED_CHART_TYPES = {"bar", "line", "area", "scatter"}

_COLUMN_REF_RE = re.compile(r"(\[([^\]]+)\]|`([^`]+)`)")
_SAFE_OUTPUT_RE = re.compile(r"[^A-Za-z0-9_]+")


class FormulaValidationError(ValueError):
    """Raised when a custom formula cannot be evaluated safely."""


@dataclass(frozen=True)
class FormulaResult:
    dataframe: pd.DataFrame
    output_column: str


def slugify_output_column(value: str | None, fallback: str = "custom_metric") -> str:
    raw = (value or fallback).strip().lower()
    raw = _SAFE_OUTPUT_RE.sub("_", raw).strip("_") or fallback
    if raw[0].isdigit():
        raw = f"custom_{raw}"
    return raw[:80]


def referenced_columns(formula: str) -> list[str]:
    """Return columns explicitly referenced as [Column] or `Column`."""
    refs = []
    for match in _COLUMN_REF_RE.finditer(formula or ""):
        column = match.group(2) or match.group(3)
        if column and column not in refs:
            refs.append(column)
    return refs


def _as_numeric_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _safe_min(*values):
    if not values:
        raise FormulaValidationError("min() requires at least one argument")
    result = values[0]
    for value in values[1:]:
        result = np.minimum(result, value)
    return result


def _safe_max(*values):
    if not values:
        raise FormulaValidationError("max() requires at least one argument")
    result = values[0]
    for value in values[1:]:
        result = np.maximum(result, value)
    return result


def _safe_clip(value, lower, upper):
    return np.clip(value, lower, upper)


SAFE_FUNCTIONS = {
    "abs": np.abs,
    "sqrt": np.sqrt,
    "log": np.log,
    "log10": np.log10,
    "exp": np.exp,
    "floor": np.floor,
    "ceil": np.ceil,
    "round": np.round,
    "pow": np.power,
    "min": _safe_min,
    "max": _safe_max,
    "clip": _safe_clip,
}


SAFE_CONSTANTS = {
    "pi": np.pi,
    "e": np.e,
}


class _FormulaValidator(ast.NodeVisitor):
    allowed_nodes = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Call,
        ast.Name,
        ast.Load,
        ast.Constant,
    )
    allowed_binops = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)
    allowed_unaryops = (ast.UAdd, ast.USub)

    def __init__(self, names: set[str]) -> None:
        self.names = names

    def generic_visit(self, node):
        if not isinstance(node, self.allowed_nodes + self.allowed_binops + self.allowed_unaryops):
            raise FormulaValidationError(
                f"Unsupported syntax in formula: {node.__class__.__name__}"
            )
        super().generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        if not isinstance(node.op, self.allowed_binops):
            raise FormulaValidationError("Unsupported arithmetic operator")
        self.visit(node.left)
        self.visit(node.right)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        if not isinstance(node.op, self.allowed_unaryops):
            raise FormulaValidationError("Unsupported unary operator")
        self.visit(node.operand)

    def visit_Call(self, node: ast.Call) -> Any:
        if not isinstance(node.func, ast.Name) or node.func.id not in SAFE_FUNCTIONS:
            raise FormulaValidationError("Only approved math functions are allowed")
        if node.keywords:
            raise FormulaValidationError("Function keyword arguments are not supported")
        for arg in node.args:
            self.visit(arg)

    def visit_Name(self, node: ast.Name) -> Any:
        if node.id not in self.names and node.id not in SAFE_FUNCTIONS and node.id not in SAFE_CONSTANTS:
            raise FormulaValidationError(f"Unknown column or function '{node.id}'")

    def visit_Constant(self, node: ast.Constant) -> Any:
        if not isinstance(node.value, (int, float)):
            raise FormulaValidationError("Only numeric constants are allowed")


def _build_expression_and_namespace(
    df: pd.DataFrame, formula: str
) -> tuple[str, dict[str, Any]]:
    if not formula or not str(formula).strip():
        raise FormulaValidationError("Formula is required")

    available_columns = set(df.columns)
    namespace: dict[str, Any] = {}
    expression = formula

    for index, column in enumerate(referenced_columns(formula)):
        if column not in available_columns:
            raise FormulaValidationError(f"Column '{column}' is not present in the dataset")
        variable_name = f"__col_{index}"
        namespace[variable_name] = _as_numeric_series(df[column])
        expression = expression.replace(f"[{column}]", variable_name)
        expression = expression.replace(f"`{column}`", variable_name)

    for column in df.columns:
        if column.isidentifier() and column not in SAFE_FUNCTIONS and column not in SAFE_CONSTANTS:
            namespace.setdefault(column, _as_numeric_series(df[column]))

    namespace.update(SAFE_FUNCTIONS)
    namespace.update(SAFE_CONSTANTS)
    return expression, namespace


def evaluate_formula(df: pd.DataFrame, formula: str, output_column: str) -> FormulaResult:
    """
    Evaluate a numeric formula against a DataFrame and return a copy with
    the derived column appended.

    Column names with spaces/symbols are referenced as [Column Name] or
    `Column Name`; valid Python identifiers may be used directly.
    """
    expression, namespace = _build_expression_and_namespace(df, formula)

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise FormulaValidationError(f"Invalid formula syntax: {exc.msg}") from exc

    _FormulaValidator(set(namespace.keys())).visit(tree)

    try:
        result = eval(compile(tree, "<custom_formula>", "eval"), {"__builtins__": {}}, namespace)
    except Exception as exc:
        raise FormulaValidationError(f"Formula evaluation failed: {exc}") from exc

    output = slugify_output_column(output_column)
    df_copy = df.copy()
    series = pd.Series(result, index=df_copy.index)
    df_copy[output] = pd.to_numeric(series, errors="coerce")
    return FormulaResult(dataframe=df_copy, output_column=output)
