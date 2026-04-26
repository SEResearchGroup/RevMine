import pandas as pd
import numpy as np
import os
import csv as csv_module
import re as _re
from io import StringIO, BytesIO
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import uuid


class DatasetService:
    """Service to handle dataset operations"""
    
    def __init__(self):
        self.storage_path = getattr(settings, 'DATASET_STORAGE_PATH', 'datasets/')
    
    # ------------------------------------------------------------------
    # Robust CSV reader
    # ------------------------------------------------------------------
    @staticmethod
    def _read_csv_safe(file_obj):
        """
        Read a CSV file-like object robustly.

        Handles the common case where data rows have MORE fields than the
        header (e.g. an unnamed extra column was inserted into the data
        but not the header).  Without this fix, pandas silently treats the
        first data column as the row index, shifting every column by one.

        Detection strategy (for exactly 1 extra data field):
        1. Check every possible insertion position.
        2. Score each position using multiple heuristics (state column
           value, date column format, column-sum relationship).
        3. Pick the position with the highest score.  Fall back to
           appending the extra column at the end if scoring is ambiguous.
        """
        content = file_obj.read()
        if isinstance(content, bytes):
            content = content.decode('utf-8')

        lines = content.strip().split('\n')
        if len(lines) < 2:
            return pd.read_csv(StringIO(content))

        # Count columns in header vs first few data rows
        header_fields = list(next(csv_module.reader(StringIO(lines[0]))))
        sample_rows = []
        for line in lines[1:min(6, len(lines))]:
            sample_rows.append(list(next(csv_module.reader(StringIO(line)))))

        n_header = len(header_fields)
        n_data = len(sample_rows[0]) if sample_rows else n_header

        if n_data <= n_header:
            return pd.read_csv(StringIO(content))

        extra_count = n_data - n_header

        if extra_count == 1:
            best_pos = DatasetService._detect_extra_col_position(
                header_fields, sample_rows
            )
            all_names = list(header_fields)
            all_names.insert(best_pos, '_extra_col_0')
            return pd.read_csv(StringIO(content), names=all_names, skiprows=1)

        # Multiple extra columns – append at end (best generic default)
        extra_names = [f'_extra_col_{i}' for i in range(extra_count)]
        all_names = list(header_fields) + extra_names
        return pd.read_csv(StringIO(content), names=all_names, skiprows=1)

    @staticmethod
    def _detect_extra_col_position(header_fields, sample_rows):
        """
        Given *header_fields* (list[str]) and *sample_rows* (list of
        list[str] for the first few data rows), return the best insertion
        index for a single extra data column.

        Uses a weighted scoring system that checks:
          • 'state' column should contain MR/PR state strings
          • 'Creation_Date' should look like a datetime
          • Numeric-name columns (#Commits, etc.) should be integers
          • Extra-col value = churn_deletions + initial_mr_size pattern
        """
        n_header = len(header_fields)
        n_data = n_header + 1
        valid_states = frozenset({'opened', 'merged', 'closed', 'open', 'locked'})

        # Helper: map a header index to its data index given an insertion position
        def data_idx(hdr_i, insert_at):
            return hdr_i if hdr_i < insert_at else hdr_i + 1

        # Build index maps for key columns
        hdr_map = {name: i for i, name in enumerate(header_fields)}

        # Integer-expected columns
        int_cols = [hdr_map[c] for c in (
            '#Discussions', '#Commits', '#UniqueCommiters',
            'nb_minor_author', 'nb_major_author', 'modified_files',
            '#people', '#reviewers', '#commiters', '#discussionners',
            'comments', 'filetypes',
        ) if c in hdr_map]

        state_hi = hdr_map.get('state')
        date_hi = hdr_map.get('Creation_Date')
        # Columns for sum-relationship check
        churn_del_hi = hdr_map.get('churn_deletions')
        init_size_hi = hdr_map.get('initial_mr_size', hdr_map.get('initial_pr_size'))

        best_pos = n_header  # default: append at end
        best_score = -999

        for insert_at in range(n_header + 1):
            score = 0

            for row in sample_rows:
                if len(row) < n_data:
                    continue

                # --- state sentinel (high weight) ---
                if state_hi is not None:
                    di = data_idx(state_hi, insert_at)
                    if di < len(row) and row[di].strip() in valid_states:
                        score += 10
                    else:
                        score -= 10

                # --- Creation_Date sentinel ---
                if date_hi is not None:
                    di = data_idx(date_hi, insert_at)
                    if di < len(row) and _re.match(r'\d{4}-\d{2}-\d{2}', row[di].strip()):
                        score += 5
                    else:
                        score -= 5

                # --- Integer columns ---
                for hi in int_cols:
                    di = data_idx(hi, insert_at)
                    if di < len(row):
                        try:
                            v = float(row[di])
                            if v == int(v):
                                score += 1
                            else:
                                score -= 2
                        except ValueError:
                            score -= 2

                # --- Sum-relationship: extra_col == churn_del + initial_size ---
                if churn_del_hi is not None and init_size_hi is not None:
                    cd_i = data_idx(churn_del_hi, insert_at)
                    is_i = data_idx(init_size_hi, insert_at)
                    extra_val_i = insert_at
                    if (extra_val_i < len(row) and cd_i < len(row)
                            and is_i < len(row)):
                        try:
                            ev = float(row[extra_val_i])
                            cv = float(row[cd_i])
                            iv = float(row[is_i])
                            if abs(ev - (cv + iv)) < 0.01:
                                score += 8  # strong signal
                        except ValueError:
                            pass

            if score > best_score:
                best_score = score
                best_pos = insert_at

        return best_pos
    
    def create_dataset(self, file, workspace_id=None, repository_id=None, platform='gitlab'):
        """
        Create a dataset from uploaded CSV file
        """
        from .models import Dataset

        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = f"{file_id}_{file.name}"
        file_path = os.path.join(self.storage_path, filename)

        # Save file
        saved_path = default_storage.save(file_path, ContentFile(file.read()))

        # Read CSV to get metadata (using robust reader)
        df = self._read_csv_safe(default_storage.open(saved_path))

        # Get columns metadata
        columns_metadata = self._extract_columns_metadata(df)

        # Create dataset record
        dataset = Dataset.objects.create(
            workspace_id=workspace_id,
            repository_id=repository_id,
            platform=platform,
            filename=file.name,
            file_path=saved_path,
            rows_count=len(df),
            columns_count=len(df.columns),
            columns_metadata=columns_metadata
        )

        return dataset

    @staticmethod
    def sanitize_filename(name):
        """
        Produce a filename that is safe for both the filesystem and an HTTP
        Content-Disposition header. We collapse every character outside
        [A-Za-z0-9._-] to an underscore — this eliminates path separators,
        non-ASCII/unicode, control chars, quoting, and anything else that
        can trip up the browser's header parser or make default_storage
        silently create subdirectories.
        """
        if not name:
            return 'dataset'
        cleaned = _re.sub(r'[^A-Za-z0-9._-]+', '_', name).strip('._ ') or 'dataset'
        return cleaned[:180]

    def create_dataset_from_dataframe(
        self,
        df,
        filename,
        source_type='code',
        source_config=None,
        collection_id=None,
        workspace_id=None,
        repository_id=None,
        platform='github',
    ):
        """
        Create a Dataset from an in-memory DataFrame by serialising it to CSV
        and persisting via default_storage. Used by live DevOps collectors
        (Kanban boards, CI/CD pipelines) that produce a normalised DataFrame
        directly rather than receiving an uploaded file.
        """
        from .models import Dataset

        file_id = str(uuid.uuid4())
        clean_name = self.sanitize_filename(filename)
        safe_name = clean_name if clean_name.endswith('.csv') else f'{clean_name}.csv'
        stored_name = f'{file_id}_{safe_name}'
        file_path = os.path.join(self.storage_path, stored_name)

        buffer = StringIO()
        df.to_csv(buffer, index=False)
        saved_path = default_storage.save(
            file_path, ContentFile(buffer.getvalue().encode('utf-8'))
        )

        columns_metadata = self._extract_columns_metadata(df)

        dataset = Dataset.objects.create(
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
        return dataset
    
    def _extract_columns_metadata(self, df):
        """
        Extract metadata about each column
        """
        metadata = {}
        
        for col in df.columns:
            col_data = df[col]
            
            # Determine column type
            dtype = str(col_data.dtype)
            
            col_metadata = {
                'dtype': dtype,
                'non_null_count': int(col_data.count()),
                'null_count': int(col_data.isna().sum()),
            }
            
            # For numeric columns
            if pd.api.types.is_numeric_dtype(col_data):
                col_metadata.update({
                    'type': 'numeric',
                    'min': float(col_data.min()) if not col_data.isna().all() else None,
                    'max': float(col_data.max()) if not col_data.isna().all() else None,
                    'mean': float(col_data.mean()) if not col_data.isna().all() else None,
                    'median': float(col_data.median()) if not col_data.isna().all() else None,
                })
            
            # For datetime columns
            elif pd.api.types.is_datetime64_any_dtype(col_data):
                col_metadata.update({
                    'type': 'datetime',
                    'min': str(col_data.min()) if not col_data.isna().all() else None,
                    'max': str(col_data.max()) if not col_data.isna().all() else None,
                })
            
            # For string/object columns
            else:
                # Try to parse as datetime
                try:
                    parsed_dates = pd.to_datetime(col_data, errors='coerce')
                    if parsed_dates.notna().sum() / len(col_data) > 0.8:  # 80% valid dates
                        col_metadata.update({
                            'type': 'datetime_string',
                            'parseable_as_datetime': True,
                        })
                    else:
                        col_metadata.update({
                            'type': 'categorical',
                            'unique_values': int(col_data.nunique()),
                            'top_values': col_data.value_counts().head(10).to_dict(),
                        })
                except:
                    col_metadata.update({
                        'type': 'categorical',
                        'unique_values': int(col_data.nunique()),
                        'top_values': col_data.value_counts().head(10).to_dict() if col_data.nunique() < 1000 else {},
                    })
            
            metadata[col] = col_metadata
        
        return metadata
    
    def load_dataframe(self, dataset):
        """
        Load dataset as pandas DataFrame
        """
        file_path = dataset.file_path
        df = self._read_csv_safe(default_storage.open(file_path))
        
        # Auto-parse datetime columns based on metadata
        for col, meta in dataset.columns_metadata.items():
            if meta.get('type') in ['datetime', 'datetime_string']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df
    
    def get_columns(self, dataset):
        """
        Get list of column names from dataset
        """
        return list(dataset.columns_metadata.keys())
    
    def get_numeric_columns(self, dataset):
        """
        Get list of numeric column names
        """
        return [
            col for col, meta in dataset.columns_metadata.items()
            if meta.get('type') == 'numeric'
        ]
    
    def get_datetime_columns(self, dataset):
        """
        Get list of datetime column names
        """
        return [
            col for col, meta in dataset.columns_metadata.items()
            if meta.get('type') in ['datetime', 'datetime_string']
        ]
    
    def get_categorical_columns(self, dataset):
        """
        Get list of categorical column names
        """
        return [
            col for col, meta in dataset.columns_metadata.items()
            if meta.get('type') == 'categorical'
        ]
    
    def get_available_metrics(self, dataset):
        """
        Get list of available metrics based on dataset columns.
        Only metrics matching the dataset's source_type are considered — this
        keeps Kanban/CI-CD metrics out of code datasets' picker (and vice
        versa) even when column names happen to overlap.
        """
        from .models import MetricDefinition

        available_columns = set(self.get_columns(dataset))
        all_metrics = MetricDefinition.objects.filter(
            is_active=True,
            source_type=getattr(dataset, 'source_type', 'code') or 'code',
        )

        available_metrics = []
        missing_columns_by_metric = {}

        for metric in all_metrics:
            required_cols = set(metric.required_columns)
            missing_cols = required_cols - available_columns

            if not missing_cols:
                available_metrics.append(metric)
            else:
                missing_columns_by_metric[metric.code] = list(missing_cols)

        return {
            'available_metrics': available_metrics,
            'missing_columns_by_metric': missing_columns_by_metric
        }
    
    def get_chart_config_options(self, dataset):
        """
        Get available configuration options for charts
        """
        return {
            'time_aggregations': ['D', 'W', 'M', 'Q', 'Y'],
            'aggregation_methods': ['sum', 'mean', 'median', 'count', 'min', 'max', 'std'],
            'chart_types': ['line', 'bar', 'scatter', 'histogram', 'pie', 'heatmap', 'box', 'area'],
            'columns': self.get_columns(dataset),
            'numeric_columns': self.get_numeric_columns(dataset),
            'date_columns': self.get_datetime_columns(dataset),
            'categorical_columns': self.get_categorical_columns(dataset),
        }
    
    def delete_dataset(self, dataset):
        """
        Delete dataset and associated file
        """
        # Delete file
        if default_storage.exists(dataset.file_path):
            default_storage.delete(dataset.file_path)
        
        # Delete database record (cascade will handle related records)
        dataset.delete()