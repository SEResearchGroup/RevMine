"""
Unit tests for the AnalysisService.
===================================
Tests every analysis function against the real efforts_results_20699.csv data
to ensure:
  - No crashes (500 errors)
  - chart_data structure is valid (has type, data.labels/datasets, options)
  - statistics dict is JSON-serializable (no NaN, Infinity, numpy types)
  - chart_image is produced (base64 string)
  - Data values are sensible

Run with:
    cd /home/s3lf-ouss/pfe/revmine/backend/services/analyze
    python -m pytest analytics/tests/test_analysis_service.py -v
    # or
    python manage.py test analytics.tests.test_analysis_service -v 2
"""

import json
import math
import os
import uuid
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile

from analytics.analysis_service import AnalysisService
from analytics.models import Dataset, MetricDefinition, Analysis, AnalysisResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EFFORTS_CSV = Path(__file__).resolve().parent.parent.parent.parent.parent.parent / 'data' / 'efforts_results_20699.csv'

# Inline CSV for environments where the external file might not exist
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
20699,7209,2023-10-19 00:02:17,17474.38,0,1,0,set,0,1,0,57.04,123421628.0,7.0,7.0,14.0,9.600,1,1,merged,51.0,5,1,2,4,26.0,25.0,16
20699,7208,2023-10-18 05:19:09,10769.28,1,1,0,set,0,1,0,57.04,123354240.0,22.0,12.0,34.0,9.599,2,1,merged,27.0,4,1,1,3,13.0,14.0,20
"""


def _load_test_df():
    """Load the test dataframe, preferring real file. Uses the same robust
    CSV reader that the production DatasetService uses."""
    from analytics.dataset_services import DatasetService
    from io import BytesIO
    if EFFORTS_CSV.exists():
        with open(EFFORTS_CSV, 'rb') as f:
            return DatasetService._read_csv_safe(f)
    # Fallback: INLINE_CSV has the same header/data mismatch as the real file,
    # so we must use _read_csv_safe here too.
    return DatasetService._read_csv_safe(BytesIO(INLINE_CSV.encode('utf-8')))


def _make_analysis(metric_code='commits_over_time', chart_type='line',
                   config=None, dataset_id=None):
    """Create a mock Analysis object (no DB save)."""
    analysis = MagicMock(spec=Analysis)
    analysis.metric_code = metric_code
    analysis.chart_type = chart_type
    analysis.config = config or {}
    analysis.dataset_id = dataset_id or uuid.uuid4()
    return analysis


def _assert_json_serializable(data, path="root"):
    """Recursively assert all values are JSON-serializable (no NaN, no numpy)."""
    if isinstance(data, dict):
        for k, v in data.items():
            _assert_json_serializable(v, path=f"{path}.{k}")
    elif isinstance(data, (list, tuple)):
        for i, v in enumerate(data):
            _assert_json_serializable(v, path=f"{path}[{i}]")
    elif isinstance(data, float):
        assert not math.isnan(data), f"NaN found at {path}"
        assert not math.isinf(data), f"Infinity found at {path}"
    elif isinstance(data, (int, str, bool, type(None))):
        pass  # OK
    else:
        assert False, f"Non-serializable type {type(data).__name__} at {path}: {data!r}"


def _assert_valid_chart_data(chart_data):
    """Assert the chart_data dict has the expected structure."""
    assert 'type' in chart_data, "chart_data missing 'type'"
    assert 'data' in chart_data, "chart_data missing 'data'"
    assert 'options' in chart_data, "chart_data missing 'options'"

    data = chart_data['data']
    # Scatter charts might not have labels
    if chart_data['type'] != 'scatter' and chart_data['type'] != 'heatmap':
        assert 'labels' in data, "chart_data.data missing 'labels'"
    assert 'datasets' in data or 'labels' in data or 'values' in data, \
        "chart_data.data should have 'datasets', 'labels', or 'values'"


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

class TestAnalysisService(TestCase):
    """Tests for every analysis function in AnalysisService."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.service = AnalysisService()
        cls.df_raw = _load_test_df()
        # Parse dates the same way AnalysisService.process_analysis would
        cls.df = cls.service._parse_dates(cls.df_raw.copy())

    # ------------------------------------------------------------------
    # Helpers that each test reuses
    # ------------------------------------------------------------------

    def _run_analysis(self, func_name, chart_type='bar', config=None):
        """Call an analysis function and return the result dict."""
        analysis = _make_analysis(
            metric_code=func_name,
            chart_type=chart_type,
            config=config or {},
        )
        func = self.service.function_mapping[func_name]
        result = func(self.df.copy(), analysis)

        # Sanitize exactly like process_analysis does
        result = self.service._sanitize_value(result)
        return result

    def _validate_result(self, result):
        """Validate structure + JSON safety of an analysis result."""
        self.assertIn('chart_data', result)
        self.assertIn('chart_image', result)
        self.assertIn('statistics', result)

        _assert_valid_chart_data(result['chart_data'])
        _assert_json_serializable(result['chart_data'])
        _assert_json_serializable(result['statistics'])

        # chart_image should be a base64 data URI
        img = result['chart_image']
        self.assertIsNotNone(img)
        self.assertTrue(img.startswith('data:image/png;base64,'),
                        "chart_image should be a base64 data URI")

        # Round-trip through json.dumps to confirm serializability
        json.dumps(result['chart_data'])
        json.dumps(result['statistics'])

    # ==================================================================
    # Individual metric tests
    # ==================================================================

    def test_commits_over_time(self):
        result = self._run_analysis('commits_over_time', chart_type='line',
                                     config={'time_aggregation': 'M'})
        self._validate_result(result)
        labels = result['chart_data']['data']['labels']
        self.assertGreater(len(labels), 0, "Should have at least one period")
        dataset_values = result['chart_data']['data']['datasets'][0]['data']
        self.assertTrue(all(isinstance(v, (int, float)) for v in dataset_values))
        # All values should be non-negative (sum of commits)
        self.assertTrue(all(v >= 0 for v in dataset_values))

    def test_commits_over_time_weekly(self):
        result = self._run_analysis('commits_over_time', chart_type='bar',
                                     config={'time_aggregation': 'W'})
        self._validate_result(result)

    def test_mr_creation_timeline(self):
        result = self._run_analysis('mr_creation_timeline', chart_type='bar',
                                     config={'time_aggregation': 'M'})
        self._validate_result(result)
        stats = result['statistics']
        self.assertEqual(stats['total_mrs'], len(self.df.dropna(subset=['Creation_Date'])))

    def test_lead_time_distribution(self):
        result = self._run_analysis('lead_time_distribution', chart_type='bar',
                                     config={})
        self._validate_result(result)
        stats = result['statistics']
        self.assertGreater(stats['count'], 0, "Should have at least 1 merged MR")
        self.assertGreater(stats['mean'], 0, "Mean lead time should be > 0")

    def test_commits_distribution(self):
        result = self._run_analysis('commits_distribution', chart_type='bar')
        self._validate_result(result)
        labels = result['chart_data']['data']['labels']
        self.assertGreater(len(labels), 0)

    def test_commiters_analysis(self):
        result = self._run_analysis('commiters_analysis', chart_type='bar')
        self._validate_result(result)

    def test_commit_time_analysis(self):
        result = self._run_analysis('commit_time_analysis', chart_type='bar')
        self._validate_result(result)
        labels = result['chart_data']['data']['labels']
        # Should have 24 hour labels
        self.assertEqual(len(labels), 24)

    def test_code_churn(self):
        result = self._run_analysis('code_churn', chart_type='bar',
                                     config={'time_aggregation': 'M'})
        self._validate_result(result)
        datasets = result['chart_data']['data']['datasets']
        # Should have two datasets: additions and deletions
        self.assertEqual(len(datasets), 2)
        self.assertEqual(datasets[0]['label'], 'Additions')
        self.assertEqual(datasets[1]['label'], 'Deletions')

    def test_churn_scatter(self):
        result = self._run_analysis('churn_scatter', chart_type='scatter')
        self._validate_result(result)
        scatter_data = result['chart_data']['data']['datasets'][0]['data']
        # Each point should have x and y
        for point in scatter_data:
            self.assertIn('x', point)
            self.assertIn('y', point)
            self.assertIsInstance(point['x'], (int, float))
            self.assertIsInstance(point['y'], (int, float))

    def test_mr_size_analysis(self):
        """mr_size_analysis should use initial_mr_size (not additions+deletions)."""
        result = self._run_analysis('mr_size_analysis', chart_type='bar')
        self._validate_result(result)
        stats = result['statistics']
        # initial_mr_size ranges from 3..339 for this dataset
        # If the code used additions+deletions (mostly 0), max would be very low
        self.assertGreater(stats['max'], 10,
                           "Max MR size should reflect initial_mr_size, not additions+deletions")

    def test_discussions_analysis(self):
        result = self._run_analysis('discussions_analysis', chart_type='bar')
        self._validate_result(result)

    def test_collaboration_metrics(self):
        result = self._run_analysis('collaboration_metrics', chart_type='bar')
        self._validate_result(result)
        # Should show averages for collaboration columns
        stats = result['statistics']
        self.assertIn('averages', stats)

    def test_comments_analysis(self):
        result = self._run_analysis('comments_analysis', chart_type='bar')
        self._validate_result(result)
        stats = result['statistics']
        self.assertGreater(stats['total_comments'], 0)

    def test_files_modified(self):
        result = self._run_analysis('files_modified', chart_type='bar')
        self._validate_result(result)

    def test_filetypes_distribution(self):
        result = self._run_analysis('filetypes_distribution', chart_type='bar')
        self._validate_result(result)

    def test_entropy_analysis(self):
        result = self._run_analysis('entropy_analysis', chart_type='bar')
        self._validate_result(result)
        stats = result['statistics']
        # hist_entropy should have values around 9.6 for this dataset
        self.assertGreater(stats['mean'], 9.0)

    def test_state_distribution(self):
        result = self._run_analysis('state_distribution', chart_type='pie')
        self._validate_result(result)
        labels = result['chart_data']['data']['labels']
        # Should contain 'opened' and 'merged' at minimum
        self.assertTrue(any('open' in str(l).lower() for l in labels),
                        f"Expected 'opened' in state labels: {labels}")
        self.assertTrue(any('merged' in str(l).lower() for l in labels),
                        f"Expected 'merged' in state labels: {labels}")

    def test_rework_analysis(self):
        result = self._run_analysis('rework_analysis', chart_type='bar')
        self._validate_result(result)
        stats = result['statistics']
        self.assertIn('mrs_with_rework', stats)
        self.assertIn('mrs_without_rework', stats)
        self.assertGreater(stats['mrs_with_rework'], 0)

    def test_correlation_matrix(self):
        result = self._run_analysis('correlation_matrix', chart_type='heatmap')
        self._validate_result(result)
        labels = result['chart_data']['data']['labels']
        values = result['chart_data']['data']['values']
        # Should be a square matrix
        self.assertEqual(len(values), len(labels))
        for row in values:
            self.assertEqual(len(row), len(labels))
        # Diagonal should be 1.0
        for i in range(len(labels)):
            self.assertAlmostEqual(values[i][i], 1.0, places=5)

    def test_mr_complexity(self):
        result = self._run_analysis('mr_complexity', chart_type='pie')
        self._validate_result(result)
        stats = result['statistics']
        self.assertEqual(stats['total_mrs'], len(self.df))

    def test_project_comparison(self):
        result = self._run_analysis('project_comparison', chart_type='bar')
        self._validate_result(result)

    def test_custom_chart_bar(self):
        result = self._run_analysis('custom_chart', chart_type='bar',
                                     config={'x_axis': 'state', 'y_axis': '#Commits',
                                             'aggregation': 'sum'})
        self._validate_result(result)

    def test_custom_chart_scatter(self):
        result = self._run_analysis('custom_chart', chart_type='scatter',
                                     config={'x_axis': 'churn_addition',
                                             'y_axis': 'churn_deletions',
                                             'aggregation': 'sum'})
        self._validate_result(result)

    # ==================================================================
    # Edge case / regression tests
    # ==================================================================

    def test_sanitize_handles_nan(self):
        """_sanitize_value should replace NaN/Inf with None."""
        val = self.service._sanitize_value(float('nan'))
        self.assertIsNone(val)
        val = self.service._sanitize_value(float('inf'))
        self.assertIsNone(val)
        val = self.service._sanitize_value(float('-inf'))
        self.assertIsNone(val)

    def test_sanitize_handles_numpy_types(self):
        """_sanitize_value should convert numpy types to Python natives."""
        self.assertIsInstance(self.service._sanitize_value(np.int64(42)), int)
        self.assertIsInstance(self.service._sanitize_value(np.float64(3.14)), float)
        self.assertIsInstance(self.service._sanitize_value(np.bool_(True)), bool)
        self.assertIsNone(self.service._sanitize_value(np.float64('nan')))

    def test_sanitize_nested_dict(self):
        """_sanitize_value should recursively sanitize nested structures."""
        data = {
            'a': np.float64(1.5),
            'b': [np.int64(1), np.int64(2)],
            'c': {'d': float('nan'), 'e': np.float64('inf')},
        }
        clean = self.service._sanitize_value(data)
        self.assertEqual(clean['a'], 1.5)
        self.assertEqual(clean['b'], [1, 2])
        self.assertIsNone(clean['c']['d'])
        self.assertIsNone(clean['c']['e'])
        # Must be JSON-serializable
        json.dumps(clean)

    def test_lead_time_with_all_open(self):
        """lead_time_distribution should raise ValueError if all MRs are open."""
        df_all_open = self.df.copy()
        df_all_open['Lead_Time'] = 'open'
        analysis = _make_analysis('lead_time_distribution', 'bar')
        with self.assertRaises(ValueError):
            self.service.analyze_lead_time_distribution(df_all_open, analysis)

    def test_all_results_json_round_trip(self):
        """Every analysis function should produce JSON-serializable output."""
        functions_to_test = [
            ('commits_over_time', 'line', {'time_aggregation': 'M'}),
            ('mr_creation_timeline', 'bar', {'time_aggregation': 'M'}),
            ('lead_time_distribution', 'bar', {}),
            ('commits_distribution', 'bar', {}),
            ('commiters_analysis', 'bar', {}),
            ('commit_time_analysis', 'bar', {}),
            ('code_churn', 'bar', {'time_aggregation': 'M'}),
            ('churn_scatter', 'scatter', {}),
            ('mr_size_analysis', 'bar', {}),
            ('discussions_analysis', 'bar', {}),
            ('collaboration_metrics', 'bar', {}),
            ('comments_analysis', 'bar', {}),
            ('files_modified', 'bar', {}),
            ('filetypes_distribution', 'bar', {}),
            ('entropy_analysis', 'bar', {}),
            ('state_distribution', 'pie', {}),
            ('rework_analysis', 'bar', {}),
            ('correlation_matrix', 'heatmap', {}),
            ('mr_complexity', 'pie', {}),
            ('project_comparison', 'bar', {}),
            ('custom_chart', 'bar', {'x_axis': 'state', 'y_axis': '#Commits', 'aggregation': 'sum'}),
        ]

        failures = []
        for func_name, chart_type, config in functions_to_test:
            try:
                result = self._run_analysis(func_name, chart_type, config)
                # Try full JSON serialization
                json.dumps(result['chart_data'])
                json.dumps(result['statistics'])
            except Exception as e:
                failures.append(f"{func_name}: {type(e).__name__}: {e}")

        if failures:
            self.fail("Analysis functions that failed:\n" + "\n".join(failures))
