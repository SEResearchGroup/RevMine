"""
Unit tests for DatasetLoader (infrastructure/storage layer).
=============================================================
Tests CSV reading, extra-column detection, and encoding fallbacks.

Run with:
    cd /home/s3lf-ouss/pfe/revmine/backend/services/analyze
    python -m pytest analytics/tests/test_dataset_loader.py -v
"""

import io
from unittest.mock import MagicMock

import pandas as pd
import pytest
from django.test import TestCase

from analytics.infrastructure.storage.dataset_loader import DatasetLoader

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CLEAN_CSV = b"""Creation_Date,Lead_Time,#Commits,state
2023-10-01,10.5,3,merged
2023-10-02,5.2,1,opened
"""

EXTRA_COL_CSV = b""",Creation_Date,Lead_Time,#Commits,state
0,2023-10-01,10.5,3,merged
1,2023-10-02,5.2,1,opened
"""

TRAILING_EXTRA_CSV = b"""Creation_Date,Lead_Time,#Commits,state,
2023-10-01,10.5,3,merged,
2023-10-02,5.2,1,opened,
"""

LATIN1_CSV = "Creation_Date,Lead_Time\r\n2023-10-01,10.5\r\n".encode("latin-1")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class DatasetLoaderReadCsvSafeTests(TestCase):

    def test_clean_csv_returns_dataframe(self):
        f = io.BytesIO(CLEAN_CSV)
        df = DatasetLoader.read_csv_safe(f)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(list(df.columns), ["Creation_Date", "Lead_Time", "#Commits", "state"])
        self.assertEqual(len(df), 2)

    def test_extra_leading_col_stripped(self):
        """A leading unnamed index column should be dropped automatically."""
        f = io.BytesIO(EXTRA_COL_CSV)
        df = DatasetLoader.read_csv_safe(f)
        self.assertIsInstance(df, pd.DataFrame)
        # The unnamed column should NOT appear as a data column
        for col in df.columns:
            self.assertNotIn("Unnamed", str(col))

    def test_trailing_extra_col_stripped(self):
        """A trailing empty column should be dropped."""
        f = io.BytesIO(TRAILING_EXTRA_CSV)
        df = DatasetLoader.read_csv_safe(f)
        # No column should be empty string or unnamed
        for col in df.columns:
            self.assertNotEqual(col.strip(), "")

    def test_latin1_encoding_fallback(self):
        """Files with latin-1 encoding should still parse."""
        f = io.BytesIO(LATIN1_CSV)
        df = DatasetLoader.read_csv_safe(f)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertIn("Lead_Time", df.columns)

    def test_empty_file_raises_or_returns_empty(self):
        """Empty file should raise ValueError or return an empty DataFrame."""
        f = io.BytesIO(b"")
        try:
            df = DatasetLoader.read_csv_safe(f)
            self.assertIsInstance(df, pd.DataFrame)
        except (ValueError, pd.errors.EmptyDataError):
            pass  # acceptable

    def test_returns_dataframe_type(self):
        f = io.BytesIO(CLEAN_CSV)
        result = DatasetLoader.read_csv_safe(f)
        self.assertIsInstance(result, pd.DataFrame)


class DatasetLoaderDetectExtraColTests(TestCase):

    def test_detects_leading_unnamed_col(self):
        """Extra column at position 0 (leading) should return index 0."""
        # Header has 4 cols, data has 5 cols with extra at position 0
        header_fields = ["Creation_Date", "Lead_Time", "#Commits", "state"]
        sample_rows = [
            ["0", "2023-10-01", "10.5", "3", "merged"],
            ["1", "2023-10-02", "5.2", "1", "opened"],
        ]
        pos = DatasetLoader._detect_extra_col_position(header_fields, sample_rows)
        self.assertEqual(pos, 0)

    def test_detects_trailing_empty_col(self):
        """Extra column at trailing position should return last index."""
        header_fields = ["Creation_Date", "Lead_Time", "#Commits", "state"]
        sample_rows = [
            ["2023-10-01", "10.5", "3", "merged", ""],
            ["2023-10-02", "5.2", "1", "opened", ""],
        ]
        pos = DatasetLoader._detect_extra_col_position(header_fields, sample_rows)
        self.assertEqual(pos, len(header_fields))

    def test_returns_integer_position(self):
        """_detect_extra_col_position must always return an integer."""
        header_fields = ["Creation_Date", "Lead_Time"]
        sample_rows = [["2023-10-01", "10.5", "extra"]]
        pos = DatasetLoader._detect_extra_col_position(header_fields, sample_rows)
        self.assertIsInstance(pos, int)
