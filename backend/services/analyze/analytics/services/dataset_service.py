"""
Service Layer – Dataset Service
=================================
Application-level service for dataset management. Coordinates between the
infrastructure storage layer (DatasetLoader) and the Django ORM.

Responsibilities:
  - Creating and persisting datasets from uploaded files or DataFrames
  - Loading datasets as pandas DataFrames
  - Extracting column metadata
  - Providing filtered column lists for the UI
  - Determining which metrics are available for a dataset
"""
from __future__ import annotations

import logging
import os
import re as _re
import uuid
from io import StringIO
from typing import Any

import pandas as pd
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from analytics.infrastructure.storage.dataset_loader import DatasetLoader

logger = logging.getLogger(__name__)


class DatasetStorageError(Exception):
    """Raised when the dataset file storage cannot be written or read."""


class DatasetService:
    """
    Application service for dataset lifecycle management.

    Uses DatasetLoader for low-level CSV parsing and exposes higher-level
    operations to views, serializers, and analysis workflows.
    """

    def __init__(self) -> None:
        self.storage_path: str = getattr(settings, "DATASET_STORAGE_PATH", "datasets/")

    def _ensure_storage_directory(self) -> None:
        media_root = getattr(settings, "MEDIA_ROOT", None)
        if not media_root:
            return

        try:
            os.makedirs(os.path.join(media_root, self.storage_path), exist_ok=True)
        except OSError as exc:
            raise DatasetStorageError(
                f"Dataset storage directory is not writable: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Compatibility shims so callers that used DatasetService._read_csv_safe
    # continue to work without modification.
    # ------------------------------------------------------------------
    @staticmethod
    def _read_csv_safe(file_obj) -> pd.DataFrame:
        return DatasetLoader.read_csv_safe(file_obj)

    @staticmethod
    def _detect_extra_col_position(header_fields, sample_rows) -> int:
        return DatasetLoader._detect_extra_col_position(header_fields, sample_rows)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_dataset(
        self,
        file,
        workspace_id=None,
        repository_id=None,
        platform="gitlab",
        user_id=None,
    ):
        """
        Persist an uploaded CSV file and create a Dataset record.

        Returns the newly created Dataset ORM instance.
        """
        from analytics.models import Dataset

        file_id = str(uuid.uuid4())
        safe_name = self.sanitize_filename(file.name)
        filename = f"{file_id}_{safe_name}"
        file_path = os.path.join(self.storage_path, filename)

        self._ensure_storage_directory()
        try:
            saved_path = default_storage.save(file_path, ContentFile(file.read()))
            with default_storage.open(saved_path) as saved_file:
                df = DatasetLoader.read_csv_safe(saved_file)
        except OSError as exc:
            logger.exception("Dataset upload storage failed")
            raise DatasetStorageError(f"Dataset storage is not writable: {exc}") from exc

        columns_metadata = self._extract_columns_metadata(df)

        return Dataset.objects.create(
            user_id=user_id,
            workspace_id=workspace_id,
            repository_id=repository_id,
            platform=platform,
            filename=safe_name,
            file_path=saved_path,
            rows_count=len(df),
            columns_count=len(df.columns),
            columns_metadata=columns_metadata,
        )

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """
        Produce a filesystem-safe filename.

        Collapses characters outside ``[A-Za-z0-9._-]`` to underscores,
        eliminating path separators, non-ASCII characters, and anything that
        could trip up ``default_storage`` or HTTP Content-Disposition headers.
        """
        if not name:
            return "dataset"
        cleaned = _re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._ ") or "dataset"
        return cleaned[:180]

    def create_dataset_from_dataframe(
        self,
        df: pd.DataFrame,
        filename: str,
        source_type: str = "code",
        source_config: dict | None = None,
        collection_id=None,
        workspace_id=None,
        repository_id=None,
        platform: str = "github",
        user_id=None,
    ):
        """
        Persist an in-memory DataFrame as CSV and create a Dataset record.

        Used by live DevOps collectors (Kanban, CI/CD) that produce a
        normalised DataFrame instead of receiving an uploaded file.
        """
        from analytics.models import Dataset

        file_id = str(uuid.uuid4())
        clean_name = self.sanitize_filename(filename)
        safe_name = clean_name if clean_name.endswith(".csv") else f"{clean_name}.csv"
        stored_name = f"{file_id}_{safe_name}"
        file_path = os.path.join(self.storage_path, stored_name)

        buffer = StringIO()
        df.to_csv(buffer, index=False)
        self._ensure_storage_directory()
        try:
            saved_path = default_storage.save(
                file_path, ContentFile(buffer.getvalue().encode("utf-8"))
            )
        except OSError as exc:
            logger.exception("Dataset dataframe storage failed")
            raise DatasetStorageError(f"Dataset storage is not writable: {exc}") from exc

        columns_metadata = self._extract_columns_metadata(df)

        return Dataset.objects.create(
            user_id=user_id,
            workspace_id=workspace_id,
            repository_id=repository_id,
            platform=platform,
            source_type=source_type,
            source_config=source_config or {},
            collection_id=collection_id,
            filename=safe_name,
            file_path=saved_path,
            rows_count=len(df),
            columns_count=len(df.columns),
            columns_metadata=columns_metadata,
        )

    def load_dataframe(self, dataset) -> pd.DataFrame:
        """
        Load a Dataset record as a pandas DataFrame.

        Applies datetime parsing based on stored columns_metadata.
        """
        df = DatasetLoader.read_csv_safe(default_storage.open(dataset.file_path))

        for col, meta in dataset.columns_metadata.items():
            if meta.get("type") in ["datetime", "datetime_string"]:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors="coerce")

        return df

    # ------------------------------------------------------------------
    # Column introspection helpers
    # ------------------------------------------------------------------

    def get_columns(self, dataset) -> list[str]:
        return list(dataset.columns_metadata.keys())

    def get_numeric_columns(self, dataset) -> list[str]:
        return [
            col
            for col, meta in dataset.columns_metadata.items()
            if meta.get("type") == "numeric"
        ]

    def get_datetime_columns(self, dataset) -> list[str]:
        return [
            col
            for col, meta in dataset.columns_metadata.items()
            if meta.get("type") in ["datetime", "datetime_string"]
        ]

    def get_categorical_columns(self, dataset) -> list[str]:
        return [
            col
            for col, meta in dataset.columns_metadata.items()
            if meta.get("type") == "categorical"
        ]

    def get_available_metrics(self, dataset) -> dict:
        """
        Return metrics whose required_columns are all present in the dataset.

        Filters by source_type so Kanban/CI-CD metrics don't appear in code
        dataset pickers and vice-versa.
        """
        from analytics.models import MetricDefinition

        available_columns = set(self.get_columns(dataset))
        all_metrics = MetricDefinition.objects.filter(
            is_active=True,
            source_type=getattr(dataset, "source_type", "code") or "code",
        )

        available_metrics: list = []
        missing_columns_by_metric: dict = {}

        for metric in all_metrics:
            missing = set(metric.required_columns) - available_columns
            if not missing:
                available_metrics.append(metric)
            else:
                missing_columns_by_metric[metric.code] = list(missing)

        return {
            "available_metrics": available_metrics,
            "missing_columns_by_metric": missing_columns_by_metric,
        }

    def get_chart_config_options(self, dataset) -> dict:
        return {
            "time_aggregations": ["D", "W", "M", "Q", "Y"],
            "aggregation_methods": ["sum", "mean", "median", "count", "min", "max", "std"],
            "chart_types": ["line", "bar", "scatter", "histogram", "pie", "heatmap", "box", "area"],
            "columns": self.get_columns(dataset),
            "numeric_columns": self.get_numeric_columns(dataset),
            "date_columns": self.get_datetime_columns(dataset),
            "categorical_columns": self.get_categorical_columns(dataset),
        }

    def delete_dataset(self, dataset) -> None:
        """Delete the dataset file and the ORM record (cascades to analyses)."""
        if default_storage.exists(dataset.file_path):
            default_storage.delete(dataset.file_path)
        dataset.delete()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_columns_metadata(df: pd.DataFrame) -> dict[str, Any]:
        """Build a metadata dict for every column in the DataFrame."""
        metadata: dict = {}

        for col in df.columns:
            col_data = df[col]
            dtype = str(col_data.dtype)
            col_meta: dict = {
                "dtype": dtype,
                "non_null_count": int(col_data.count()),
                "null_count": int(col_data.isna().sum()),
            }

            if pd.api.types.is_numeric_dtype(col_data):
                col_meta.update({
                    "type": "numeric",
                    "min": float(col_data.min()) if not col_data.isna().all() else None,
                    "max": float(col_data.max()) if not col_data.isna().all() else None,
                    "mean": float(col_data.mean()) if not col_data.isna().all() else None,
                    "median": float(col_data.median()) if not col_data.isna().all() else None,
                })
            elif pd.api.types.is_datetime64_any_dtype(col_data):
                col_meta.update({
                    "type": "datetime",
                    "min": str(col_data.min()) if not col_data.isna().all() else None,
                    "max": str(col_data.max()) if not col_data.isna().all() else None,
                })
            else:
                try:
                    parsed = pd.to_datetime(col_data, errors="coerce")
                    if parsed.notna().sum() / max(len(col_data), 1) > 0.8:
                        col_meta.update({
                            "type": "datetime_string",
                            "parseable_as_datetime": True,
                        })
                    else:
                        col_meta.update({
                            "type": "categorical",
                            "unique_values": int(col_data.nunique()),
                            "top_values": col_data.value_counts().head(10).to_dict(),
                        })
                except Exception:
                    col_meta.update({
                        "type": "categorical",
                        "unique_values": int(col_data.nunique()),
                        "top_values": (
                            col_data.value_counts().head(10).to_dict()
                            if col_data.nunique() < 1000
                            else {}
                        ),
                    })

            metadata[col] = col_meta

        return metadata
