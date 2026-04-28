"""
Unit tests for MetricsEngine (domain layer).
============================================
Tests that all analyze_* methods return valid chart_data structures with no
crashes, no NaN/Infinity in JSON outputs, and sensible outputs.

Run with:
    cd /home/s3lf-ouss/pfe/revmine/backend/services/analyze
    python -m pytest analytics/tests/test_metrics_engine.py -v
"""

import json
import math
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from django.test import TestCase

from analytics.domain.metrics.metrics_engine import MetricsEngine

# ---------------------------------------------------------------------------
# Fixtures / shared data
# ---------------------------------------------------------------------------

INLINE_CSV = """\
Project_ID,MR_ID,Creation_Date,Lead_Time,#Discussions,#Commits,Mean_Time_between_commits,Commiters,#UniqueCommiters,nb_minor_author,nb_major_author,delta_time,churn_addition,churn_deletions,initial_mr_size,hist_entropy,modified_files,filetypes,state,rework_size,#people,#reviewers,#commiters,#discussionners,additions,deletions,comments
20699,7225,2023-11-02 06:35:22,open,0,1,0,,1,1,0,57.19,124654813.0,12.0,12.0,24.0,9.604,2,2,opened,0.0,1,0,1,1,0,0,1
20699,7224,2023-11-02 00:02:33,open,0,1,0,deps,1,1,0,57.19,124631244.0,7.0,7.0,14.0,9.604,1,1,opened,0.0,3,2,1,1,0,0,6
20699,7223,2023-10-31 16:15:45,open,1,1,0,crea,1,1,0,57.11,124516836.0,2.0,2.0,4.0,9.604,1,1,opened,0.0,2,0,1,2,0,0,7
20699,7222,2023-10-30 20:32:54,open,1,1,0,set,0,1,0,57.10,124445865.0,47.0,3.0,50.0,9.603,1,1,opened,53.0,3,1,1,3,30.0,23.0,13
20699,7221,2023-10-30 00:02:26,4410.98,0,1,0,deps,1,1,0,57.11,124372037.0,7.0,7.0,14.0,9.603,1,1,merged,0.0,3,2,1,2,0,0,7
20699,7220,2023-10-26 11:34:01,6593.12,1,1,0,set,0,1,0,57.09,124067932.0,87.0,31.0,118.0,9.603,6,3,merged,45.0,4,1,1,3,27.0,18.0,20
20699,7219,2023-10-26 05:43:09,open,1,0,638.0,beck,1,0,0,57.09,124046880.0,194.0,145.0,339.0,9.602,25,3,opened,0.0,3,1,1,2,0,0,17
20699,7218,2023-10-26 04:54:11,1143.9,1,1,0,set,0,1,0,57.10,124043942.0,17.0,3.0,20.0,9.602,1,1,merged,66.0,6,3,2,6,33.0,33.0,20
20699,7217,2023-10-26 01:23:52,open,1,2,148.0,set,0,0,1,57.10,124031323.0,13.0,14.0,27.0,9.602,2,2,opened,210.0,3,0,1,2,178.0,32.0,3
20699,7216,2023-10-25 05:28:09,37.27,1,1,0,beck,1,1,0,57.08,123959580.0,70.0,112.0,182.0,9.602,5,2,merged,0.0,3,1,1,3,0,0,9
20699,7215,2023-10-24 18:34:22,open,1,1,0,set,0,1,0,57.07,123920353.0,7.0,6.0,13.0,9.601,1,1,opened,27.0,4,2,1,3,13.0,14.0,15
20699,7214,2023-10-23 09:59:19,open,0,1,0,balu,1,0,1,57.07,123803050.0,75.0,3.0,78.0,9.601,2,1,opened,0.0,3,0,1,2,0,0,7
20699,7213,2023-10-23 06:20:40,open,0,2,-6747.0,balu,1,0,1,57.05,123789931.0,212.0,21.0,233.0,9.601,4,2,opened,0.0,3,0,1,2,0,0,5
20699,7212,2023-10-21 00:10:54,open,0,1,0,stan,1,1,0,57.04,123594945.0,16.0,22.0,38.0,9.600,2,2,opened,0.0,4,2,1,3,0,0,20
20699,7211,2023-10-19 00:20:48,8204.97,0,1,0,balu,1,0,1,57.04,123422739.0,7.0,6.0,13.0,9.600,1,1,merged,0.0,5,2,1,4,0,0,19
20699,7210,2023-10-19 00:02:22,8812.43,0,1,0,deps,1,1,0,57.04,123421633.0,7.0,7.0,14.0,9.600,1,1,merged,0.0,3,2,1,2,0,0,6
"""


def _load_df():
    df = pd.read_csv(StringIO(INLINE_CSV))
    df["Creation_Date"] = pd.to_datetime(df["Creation_Date"], errors="coerce")
    return df


def _json_safe(obj):
    """Return True if obj can be serialised to JSON without NaN/Inf."""
    try:
        s = json.dumps(obj)
    except (TypeError, ValueError):
        return False
    # Check for NaN/Infinity tokens that json.dumps inserts for floats
    return "NaN" not in s and "Infinity" not in s


def _chart_data_valid(cd):
    """Return True if chart_data has the minimal required structure."""
    if not isinstance(cd, dict):
        return False
    if "type" not in cd:
        return False
    data = cd.get("data")
    if not isinstance(data, dict):
        return False
    return _json_safe(cd)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class MetricsEngineInitTests(TestCase):
    """MetricsEngine can be instantiated and exposes function_mapping."""

    def test_instantiation(self):
        engine = MetricsEngine()
        self.assertIsInstance(engine, MetricsEngine)

    def test_function_mapping_populated(self):
        engine = MetricsEngine()
        self.assertIsInstance(engine.function_mapping, dict)
        self.assertGreater(len(engine.function_mapping), 0)

    def test_function_mapping_values_are_callables(self):
        engine = MetricsEngine()
        for key, fn in engine.function_mapping.items():
            self.assertTrue(callable(fn), f"function_mapping[{key!r}] is not callable")


class MetricsEngineAnalyzeMethodsTests(TestCase):
    """
    Spot-check a representative set of analyze_* methods for valid output.
    Each test loads the inline CSV and calls the method directly.
    """

    def setUp(self):
        self.engine = MetricsEngine()
        self.df = _load_df()

    def _run(self, method_name, **kwargs):
        fn = getattr(self.engine, method_name)
        result = fn(self.df, **kwargs)
        self.assertIsNotNone(result, f"{method_name} returned None")
        chart_data, statistics, image = result
        self.assertTrue(
            _chart_data_valid(chart_data),
            f"{method_name}: chart_data is not valid JSON-safe dict: {chart_data!r}",
        )
        self.assertIsInstance(statistics, dict, f"{method_name}: statistics is not a dict")
        self.assertTrue(_json_safe(statistics), f"{method_name}: statistics is not JSON-safe")
        return chart_data, statistics, image

    def test_analyze_lead_time_distribution(self):
        self._run("analyze_lead_time_distribution")

    def test_analyze_commits_over_time(self):
        self._run("analyze_commits_over_time")

    def test_analyze_mr_creation_timeline(self):
        self._run("analyze_mr_creation_timeline")

    def test_analyze_mr_state_distribution(self):
        self._run("analyze_mr_state_distribution")

    def test_analyze_discussions_vs_lead_time(self):
        self._run("analyze_discussions_vs_lead_time")

    def test_analyze_commits_vs_lead_time(self):
        self._run("analyze_commits_vs_lead_time")

    def test_analyze_rework_size_distribution(self):
        self._run("analyze_rework_size_distribution")

    def test_analyze_churn_distribution(self):
        self._run("analyze_churn_distribution")

    def test_analyze_contributor_activity(self):
        self._run("analyze_contributor_activity")

    def test_all_function_mapping_methods_dont_crash(self):
        """Every method in function_mapping must handle the default DataFrame."""
        for metric_code, fn in self.engine.function_mapping.items():
            with self.subTest(metric=metric_code):
                try:
                    result = fn(self.df)
                    self.assertIsNotNone(result, f"{metric_code} returned None")
                except Exception as exc:
                    self.fail(f"{metric_code} raised {type(exc).__name__}: {exc}")


class MetricsEngineSanitizeTests(TestCase):
    """_sanitize_value removes NaN/Inf from scalars and nested structures."""

    def setUp(self):
        self.engine = MetricsEngine()

    def test_nan_becomes_none(self):
        self.assertIsNone(self.engine._sanitize_value(float("nan")))

    def test_inf_becomes_none(self):
        self.assertIsNone(self.engine._sanitize_value(float("inf")))

    def test_finite_float_passes(self):
        self.assertAlmostEqual(self.engine._sanitize_value(3.14), 3.14)

    def test_numpy_int(self):
        val = self.engine._sanitize_value(np.int64(42))
        self.assertEqual(val, 42)
        self.assertIsInstance(val, int)

    def test_numpy_float(self):
        val = self.engine._sanitize_value(np.float64(1.5))
        self.assertAlmostEqual(val, 1.5)

    def test_dict_recursion(self):
        result = self.engine._sanitize_value({"a": float("nan"), "b": 1})
        self.assertIsNone(result["a"])
        self.assertEqual(result["b"], 1)

    def test_list_recursion(self):
        result = self.engine._sanitize_value([float("inf"), 2, None])
        self.assertIsNone(result[0])
        self.assertEqual(result[1], 2)
        self.assertIsNone(result[2])
