"""
Unit tests for DatasetService (service layer).
===============================================
Tests dataset lifecycle: upload, read, introspect, delete.
All file I/O is mocked to avoid touching the real filesystem.

Run with:
    cd /home/s3lf-ouss/pfe/revmine/backend/services/analyze
    python -m pytest analytics/tests/test_dataset_service.py -v
"""

import io
import json
import uuid
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pandas as pd
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from analytics.services.dataset_service import DatasetService
from analytics.models import Dataset

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_CSV = """\
Creation_Date,Lead_Time,#Commits,state
2023-10-01,10.5,3,merged
2023-10-02,5.2,1,opened
2023-10-03,20.0,5,merged
"""

SAMPLE_CSV_WITH_EXTRA_COL = """\
,Creation_Date,Lead_Time,#Commits,state
0,2023-10-01,10.5,3,merged
1,2023-10-02,5.2,1,opened
"""


def _make_upload(content=SAMPLE_CSV, name="test.csv"):
    return SimpleUploadedFile(name, content.encode(), content_type="text/csv")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@override_settings(MEDIA_ROOT="/tmp/test_analyze_media/")
class DatasetServiceCreateTests(TestCase):

    @patch("analytics.services.dataset_service.default_storage")
    @patch("analytics.services.dataset_service.DatasetLoader.read_csv_safe")
    def test_create_dataset_returns_dataset_instance(self, mock_read_csv, mock_storage):
        """create_dataset saves file and creates Dataset DB row."""
        df = pd.read_csv(StringIO(SAMPLE_CSV))
        mock_read_csv.return_value = df
        mock_storage.save.return_value = "datasets/test.csv"
        mock_storage.path.return_value = "/tmp/test_analyze_media/datasets/test.csv"

        file = _make_upload()
        svc = DatasetService()
        dataset = svc.create_dataset(
            file=file,
            workspace_id=1,
            repository_id=1,
            platform="gitlab",
        )

        self.assertIsInstance(dataset, Dataset)
        self.assertEqual(dataset.rows_count, len(df))
        self.assertEqual(dataset.columns_count, len(df.columns))

    @patch("analytics.services.dataset_service.default_storage")
    def test_create_dataset_from_dataframe(self, mock_storage):
        """create_dataset_from_dataframe saves CSV and creates Dataset."""
        df = pd.read_csv(StringIO(SAMPLE_CSV))
        mock_storage.save.return_value = "datasets/from_df.csv"
        mock_storage.path.return_value = "/tmp/test_analyze_media/datasets/from_df.csv"

        buf = io.BytesIO()
        df.to_csv(buf, index=False)
        mock_storage.open.return_value.__enter__ = lambda s: buf
        mock_storage.open.return_value.__exit__ = MagicMock(return_value=False)

        svc = DatasetService()
        dataset = svc.create_dataset_from_dataframe(
            df=df,
            filename="from_df.csv",
            workspace_id=1,
            repository_id=1,
            platform="github",
        )
        self.assertIsInstance(dataset, Dataset)

    @patch("analytics.services.dataset_service.default_storage")
    @patch("analytics.services.dataset_service.DatasetLoader.read_csv_safe")
    def test_load_dataframe_returns_dataframe(self, mock_read_csv, mock_storage):
        """load_dataframe reads file from storage and returns DataFrame."""
        expected = pd.read_csv(StringIO(SAMPLE_CSV))
        mock_read_csv.return_value = expected
        mock_storage.path.return_value = "/tmp/test_analyze_media/datasets/test.csv"
        mock_storage.open.return_value.__enter__ = lambda s: io.BytesIO(
            SAMPLE_CSV.encode()
        )
        mock_storage.open.return_value.__exit__ = MagicMock(return_value=False)

        dataset = Dataset(
            file_path="datasets/test.csv",
            workspace_id=1,
            repository_id=1,
            platform="gitlab",
            filename="test.csv",
        )
        svc = DatasetService()
        df = svc.load_dataframe(dataset)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(list(df.columns), list(expected.columns))


@override_settings(MEDIA_ROOT="/tmp/test_analyze_media/")
class DatasetServiceIntrospectionTests(TestCase):

    def _make_dataset_with_metadata(self, meta: dict) -> Dataset:
        return Dataset(
            id=uuid.uuid4(),
            workspace_id=1,
            repository_id=1,
            platform="gitlab",
            filename="test.csv",
            file_path="datasets/test.csv",
            columns_metadata=meta,
        )

    def test_get_columns_from_metadata(self):
        meta = {
            "Creation_Date": {"type": "datetime", "dtype": "datetime64[ns]"},
            "Lead_Time": {"type": "numeric", "dtype": "float64"},
            "state": {"type": "categorical", "dtype": "object"},
        }
        dataset = self._make_dataset_with_metadata(meta)
        svc = DatasetService()
        cols = svc.get_columns(dataset)
        self.assertEqual(set(cols), set(meta.keys()))

    def test_get_numeric_columns(self):
        meta = {
            "Lead_Time": {"type": "numeric", "dtype": "float64"},
            "#Commits": {"type": "numeric", "dtype": "int64"},
            "state": {"type": "categorical", "dtype": "object"},
            "Creation_Date": {"type": "datetime", "dtype": "datetime64[ns]"},
        }
        dataset = self._make_dataset_with_metadata(meta)
        svc = DatasetService()
        numeric = svc.get_numeric_columns(dataset)
        self.assertIn("Lead_Time", numeric)
        self.assertIn("#Commits", numeric)
        self.assertNotIn("state", numeric)

    def test_get_datetime_columns(self):
        meta = {
            "Lead_Time": {"type": "numeric", "dtype": "float64"},
            "Creation_Date": {"type": "datetime", "dtype": "datetime64[ns]"},
        }
        dataset = self._make_dataset_with_metadata(meta)
        svc = DatasetService()
        dt_cols = svc.get_datetime_columns(dataset)
        self.assertIn("Creation_Date", dt_cols)
        self.assertNotIn("Lead_Time", dt_cols)

    def test_get_categorical_columns(self):
        meta = {
            "state": {"type": "categorical", "dtype": "object"},
            "Lead_Time": {"type": "numeric", "dtype": "float64"},
        }
        dataset = self._make_dataset_with_metadata(meta)
        svc = DatasetService()
        cat_cols = svc.get_categorical_columns(dataset)
        self.assertIn("state", cat_cols)
        self.assertNotIn("Lead_Time", cat_cols)

    @patch("analytics.services.dataset_service.default_storage")
    def test_delete_dataset_calls_storage(self, mock_storage):
        """delete_dataset deletes file from storage and removes DB record."""
        dataset = Dataset(
            id=uuid.uuid4(),
            workspace_id=1,
            repository_id=1,
            platform="gitlab",
            filename="test.csv",
            file_path="datasets/test.csv",
        )
        dataset.delete = MagicMock()
        mock_storage.exists.return_value = True

        svc = DatasetService()
        svc.delete_dataset(dataset)

        mock_storage.delete.assert_called_once_with("datasets/test.csv")
        dataset.delete.assert_called_once()
