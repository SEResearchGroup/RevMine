import pandas as pd
import numpy as np
import os
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import uuid


class DatasetService:
    """Service to handle dataset operations"""
    
    def __init__(self):
        self.storage_path = getattr(settings, 'DATASET_STORAGE_PATH', 'datasets/')
    
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
        
        # Read CSV to get metadata
        df = pd.read_csv(default_storage.open(saved_path))
        
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
        df = pd.read_csv(default_storage.open(file_path))
        
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
        Get list of available metrics based on dataset columns
        """
        from .models import MetricDefinition
        
        available_columns = set(self.get_columns(dataset))
        all_metrics = MetricDefinition.objects.filter(is_active=True)
        
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