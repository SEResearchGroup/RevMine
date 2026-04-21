import pandas as pd
import numpy as np
import matplotlib

from .dataset_services import DatasetService
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
from datetime import datetime
from django.utils import timezone


class AnalysisService:
    """Service to handle analysis operations"""
    
    # Date columns that should be parsed as datetime
    DATE_COLUMNS = ['Creation_Date', 'created_at', 'updated_at', 'merged_at', 'closed_at']
    
    def __init__(self):
        self.function_mapping = {
            'commits_over_time': self.analyze_commits_over_time,
            'mr_creation_timeline': self.analyze_mr_creation_timeline,
            'lead_time_distribution': self.analyze_lead_time_distribution,
            'commits_distribution': self.analyze_commits_distribution,
            'commiters_analysis': self.analyze_commiters,
            'commit_time_analysis': self.analyze_commit_time,
            'code_churn': self.analyze_code_churn,
            'churn_scatter': self.analyze_churn_scatter,
            'mr_size_analysis': self.analyze_mr_size,
            'discussions_analysis': self.analyze_discussions,
            'collaboration_metrics': self.analyze_collaboration_metrics,
            'comments_analysis': self.analyze_comments,
            'files_modified': self.analyze_files_modified,
            'filetypes_distribution': self.analyze_filetypes_distribution,
            'entropy_analysis': self.analyze_entropy,
            'state_distribution': self.analyze_state_distribution,
            'rework_analysis': self.analyze_rework,
            'correlation_matrix': self.analyze_correlation_matrix,
            'mr_complexity': self.analyze_mr_complexity,
            'project_comparison': self.analyze_project_comparison,
            'top_commiters': self.analyze_top_commiters,
            'top_authors': self.analyze_top_authors,
            'top_reviewers': self.analyze_top_reviewers,
            # Kanban (DevOps) metrics
            'kanban_lead_time': self.analyze_kanban_lead_time,
            'kanban_cycle_time': self.analyze_kanban_cycle_time,
            'kanban_throughput': self.analyze_kanban_throughput,
            'kanban_wip': self.analyze_kanban_wip,
            'kanban_cfd': self.analyze_kanban_cfd,
            'kanban_column_time': self.analyze_kanban_column_time,
            'kanban_blocked_ratio': self.analyze_kanban_blocked_ratio,
            'kanban_assignee_load': self.analyze_kanban_assignee_load,
            # CI/CD (DevOps) metrics
            'cicd_success_rate': self.analyze_cicd_success_rate,
            'cicd_build_duration': self.analyze_cicd_build_duration,
            'cicd_failure_rate_by_job': self.analyze_cicd_failure_rate_by_job,
            'cicd_mttr': self.analyze_cicd_mttr,
            'cicd_deploy_frequency': self.analyze_cicd_deploy_frequency,
            'cicd_queue_time': self.analyze_cicd_queue_time,
            'cicd_runner_utilization': self.analyze_cicd_runner_utilization,
            'cicd_flaky_jobs': self.analyze_cicd_flaky_jobs,
        }
    
    def _parse_dates(self, df):
        """
        Parse date columns properly - handles various date formats
        """
        df_copy = df.copy()
        
        for col in self.DATE_COLUMNS:
            if col in df_copy.columns:
                # Try to parse as datetime string first (e.g., "2023-11-02 06:35:22")
                df_copy[col] = pd.to_datetime(df_copy[col], errors='coerce', format='mixed')
        
        return df_copy
    
    def process_analysis(self, analysis):
        """
        Process an analysis request
        """
        from .models import AnalysisResult
        
        try:
            # Update status
            analysis.status = 'processing'
            analysis.save()
            
            # Load dataset
            dataset_service = DatasetService()
            df = dataset_service.load_dataframe(analysis.dataset)
            
            # Parse date columns properly
            df = self._parse_dates(df)
            
            # Get analysis function
            function_name = self._get_function_name(analysis.metric_code)
            analysis_function = self.function_mapping.get(function_name)
            
            if not analysis_function:
                raise ValueError(f"Analysis function for metric '{analysis.metric_code}' not found")
            
            # Execute analysis
            result_data = analysis_function(df, analysis)
            
            # Sanitize all data for JSON serialization (NaN, numpy types, etc.)
            result_data = self._sanitize_value(result_data)
            
            # Create result
            AnalysisResult.objects.create(
                analysis=analysis,
                chart_data=result_data['chart_data'],
                chart_image=result_data.get('chart_image'),
                statistics=result_data.get('statistics')
            )
            
            # Update analysis status
            analysis.status = 'completed'
            analysis.completed_at = timezone.now()
            analysis.save()
            
        except Exception as e:
            analysis.status = 'failed'
            analysis.error_message = str(e)
            analysis.save()
            raise
    
    def _get_function_name(self, metric_code):
        """
        Get function name from metric code
        """
        from .models import MetricDefinition
        
        try:
            metric = MetricDefinition.objects.get(code=metric_code)
            return metric.analysis_function
        except MetricDefinition.DoesNotExist:
            return metric_code
    
    def _apply_config(self, df, config):
        """
        Apply configuration filters and transformations
        """
        df_copy = df.copy()
        
        # Apply filters
        filters = config.get('filters', {})
        for col, filter_value in filters.items():
            if col in df_copy.columns:
                if isinstance(filter_value, dict):
                    # Range filter
                    series = df_copy[col]
                    if 'min' in filter_value:
                        min_value = filter_value['min']
                        if pd.api.types.is_datetime64_any_dtype(series):
                            min_value = pd.to_datetime(min_value, errors='coerce')
                        df_copy = df_copy[df_copy[col] >= min_value]
                    if 'max' in filter_value:
                        max_value = filter_value['max']
                        if pd.api.types.is_datetime64_any_dtype(series):
                            max_value = pd.to_datetime(max_value, errors='coerce')
                        df_copy = df_copy[df_copy[col] <= max_value]
                elif isinstance(filter_value, list):
                    # Multi-select filter
                    df_copy = df_copy[df_copy[col].isin(filter_value)]
                else:
                    # Exact match filter
                    df_copy = df_copy[df_copy[col] == filter_value]

        return df_copy
    
    def _generate_matplotlib_image(self, fig):
        """
        Convert matplotlib figure to base64 string
        """
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close(fig)
        return f"data:image/png;base64,{image_base64}"

    def _sanitize_value(self, value):
        """
        Recursively sanitize values for JSON serialization.
        Handles NaN, Infinity, numpy types that would break json.dumps.
        """
        import math
        if value is None:
            return None
        if isinstance(value, dict):
            return {k: self._sanitize_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._sanitize_value(v) for v in value]
        if isinstance(value, tuple):
            return [self._sanitize_value(v) for v in value]
        if isinstance(value, np.ndarray):
            return [self._sanitize_value(v) for v in value.tolist()]
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating,)):
            if np.isnan(value) or np.isinf(value):
                return None
            return float(value)
        if isinstance(value, (np.bool_,)):
            return bool(value)
        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                return None
            return value
        if hasattr(value, 'item'):  # Generic numpy scalar
            return self._sanitize_value(value.item())
        if isinstance(value, pd.Timestamp):
            return value.isoformat()
        if isinstance(value, pd.Period):
            return str(value)
        return value

    # ==================== Analysis Functions ====================
    
    def _format_date_labels(self, periods):
        """Format period labels properly for display"""
        labels = []
        for p in periods:
            try:
                # Convert period to timestamp then format
                labels.append(p.to_timestamp().strftime('%Y-%m-%d'))
            except:
                labels.append(str(p))
        return labels
    
    def analyze_commits_over_time(self, df, analysis):
        """
        Analyze commits over time with configurable aggregation
        """
        config = analysis.config
        date_col = config.get('x_axis') or 'Creation_Date'
        value_col = config.get('y_axis') or '#Commits'
        freq = config.get('time_aggregation') or 'M'
        aggregation = config.get('aggregation') or 'sum'
        
        df = self._apply_config(df, config)
        
        # Prepare data - ensure date column is datetime
        df_copy = df.copy()
        if date_col not in df_copy.columns:
            raise ValueError(f"Column '{date_col}' not found in dataset")
        
        # Parse dates - MÊME LOGIQUE QUE LA FONCTION DE BASE
        df_copy[date_col] = pd.to_datetime(df_copy[date_col], errors='coerce')
        df_copy = df_copy.dropna(subset=[date_col])
        
        if len(df_copy) == 0:
            raise ValueError(f"No valid dates found in column '{date_col}'")
        
        # Validate date range (should be reasonable - between 2000 and 2030)
        min_date = df_copy[date_col].min()
        max_date = df_copy[date_col].max()
        
        if min_date.year < 2000 or max_date.year > 2030:
            raise ValueError(f"Invalid date range detected: {min_date} to {max_date}. Please check your date column.")
        
        df_copy['period'] = df_copy[date_col].dt.to_period(freq)
        
        # Ensure value column is numeric
        if value_col in df_copy.columns:
            df_copy[value_col] = pd.to_numeric(df_copy[value_col], errors='coerce').fillna(0)
        
        # Aggregate
        if aggregation == 'sum':
            result = df_copy.groupby('period')[value_col].sum()
        elif aggregation == 'mean':
            result = df_copy.groupby('period')[value_col].mean()
        elif aggregation == 'median':
            result = df_copy.groupby('period')[value_col].median()
        elif aggregation == 'count':
            result = df_copy.groupby('period').size()
        else:
            result = df_copy.groupby('period')[value_col].sum()
        
        # Sort by period
        result = result.sort_index()
        
        # Format labels properly
        labels = self._format_date_labels(result.index)
        
        # Prepare chart data
        chart_data = {
            'type': analysis.chart_type or 'line',
            'data': {
                'labels': labels,
                'datasets': [{
                    'label': f'{value_col} ({aggregation})',
                    'data': [float(v) if pd.notna(v) else 0 for v in result.values],
                }]
            },
            'options': {
                'title': f'{value_col} over time',
                'xLabel': 'Period',
                'yLabel': f'{value_col} ({aggregation})',
            }
        }
        
        # Generate matplotlib image
        fig, ax = plt.subplots(figsize=(12, 6))
        x_positions = range(len(result))
        if analysis.chart_type == 'line':
            ax.plot(x_positions, result.values, marker='o', linewidth=2, markersize=6)
        else:
            ax.bar(x_positions, result.values, color='steelblue')
        ax.set_xlabel('Period')
        ax.set_ylabel(f'{value_col} ({aggregation})')
        ax.set_title(f'{value_col} over time')
        ax.set_xticks(x_positions)
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        chart_image = self._generate_matplotlib_image(fig)
        
        # Statistics
        statistics = {
            'total': float(result.sum()) if pd.notna(result.sum()) else 0,
            'mean': float(result.mean()) if pd.notna(result.mean()) else 0,
            'median': float(result.median()) if pd.notna(result.median()) else 0,
            'min': float(result.min()) if pd.notna(result.min()) else 0,
            'max': float(result.max()) if pd.notna(result.max()) else 0,
            'std': float(result.std()) if pd.notna(result.std()) else 0,
            'periods_count': len(result),
            'date_range': f"{min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}"
        }
        
        return {
            'chart_data': chart_data,
            'chart_image': chart_image,
            'statistics': statistics
        }
    def analyze_mr_creation_timeline(self, df, analysis):
        """
        Analyze MR creation timeline - counts MRs created per period
        """
        config = analysis.config
        date_col = config.get('x_axis') or 'Creation_Date'
        freq = config.get('time_aggregation') or 'W'
        
        df = self._apply_config(df, config)
        
        df_copy = df.copy()
        
        # Parse dates if not already done
        if not pd.api.types.is_datetime64_any_dtype(df_copy[date_col]):
            df_copy[date_col] = pd.to_datetime(df_copy[date_col], errors='coerce', format='mixed')
        
        df_copy = df_copy.dropna(subset=[date_col])
        
        if len(df_copy) == 0:
            raise ValueError(f"No valid dates found in column '{date_col}'")
        
        # Validate date range
        min_date = df_copy[date_col].min()
        max_date = df_copy[date_col].max()
        
        df_copy['period'] = df_copy[date_col].dt.to_period(freq)
        mrs_by_period = df_copy.groupby('period').size().sort_index()
        
        # Format labels
        labels = self._format_date_labels(mrs_by_period.index)
        
        chart_data = {
            'type': analysis.chart_type or 'bar',
            'data': {
                'labels': labels,
                'datasets': [{
                    'label': 'Number of MRs created',
                    'data': mrs_by_period.values.tolist(),
                }]
            },
            'options': {
                'title': 'Merge Requests Creation Timeline',
                'xLabel': 'Period',
                'yLabel': 'Number of MRs',
            }
        }
        
        # Generate matplotlib image
        fig, ax = plt.subplots(figsize=(12, 6))
        x_positions = range(len(mrs_by_period))
        ax.bar(x_positions, mrs_by_period.values, color='steelblue')
        ax.set_xlabel('Period')
        ax.set_ylabel('Number of MRs')
        ax.set_title('Merge Requests Creation Timeline')
        ax.set_xticks(x_positions)
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        chart_image = self._generate_matplotlib_image(fig)
        
        statistics = {
            'total_mrs': int(mrs_by_period.sum()),
            'mean_per_period': float(mrs_by_period.mean()),
            'max_per_period': int(mrs_by_period.max()),
            'min_per_period': int(mrs_by_period.min()),
            'periods_count': len(mrs_by_period),
            'date_range': f"{min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}"
        }
        
        return {
            'chart_data': chart_data,
            'chart_image': chart_image,
            'statistics': statistics
        }
    
    def analyze_lead_time_distribution(self, df, analysis):
        """
        Analyze lead time distribution with adaptive binning and time-based filtering.

        Config params:
          x_axis       – column name for lead time (default: 'Lead_Time')
          time_filter  – 'all' | 'daily' | 'weekly' | 'monthly'
                         Filters rows by Creation_Date before computing the histogram.
        """
        config = analysis.config
        lead_time_col = config.get('x_axis') or 'Lead_Time'
        time_filter = config.get('time_filter', 'all')
        date_col = 'Creation_Date'

        df = self._apply_config(df, config)
        df_filtered = df.copy()

        # ------------------------------------------------------------------
        # 1. Time-based filtering on Creation_Date
        #    Use the dataset's own max date as the reference point so that
        #    historical datasets produce meaningful results.
        # ------------------------------------------------------------------
        if time_filter != 'all' and date_col in df_filtered.columns:
            if not pd.api.types.is_datetime64_any_dtype(df_filtered[date_col]):
                df_filtered[date_col] = pd.to_datetime(df_filtered[date_col], errors='coerce')
            if df_filtered[date_col].dt.tz is not None:
                df_filtered[date_col] = df_filtered[date_col].dt.tz_localize(None)
            max_date = df_filtered[date_col].dropna().max()
            if pd.notna(max_date):
                days_map = {'daily': 1, 'weekly': 7, 'monthly': 30}
                days = days_map.get(time_filter)
                if days:
                    cutoff = max_date - pd.Timedelta(days=days)
                    df_filtered = df_filtered[df_filtered[date_col] >= cutoff]

        # ------------------------------------------------------------------
        # 2. Clean the lead-time column
        # ------------------------------------------------------------------
        if lead_time_col not in df_filtered.columns:
            raise ValueError(f"Column '{lead_time_col}' not found in dataset")

        df_filtered = df_filtered[df_filtered[lead_time_col] != 'open']
        df_filtered[lead_time_col] = pd.to_numeric(df_filtered[lead_time_col], errors='coerce')
        df_filtered = df_filtered.dropna(subset=[lead_time_col])
        df_filtered = df_filtered[df_filtered[lead_time_col] >= 0]
        df_filtered = df_filtered[df_filtered[lead_time_col] < 10000]

        if len(df_filtered) == 0:
            chart_data = {
                'type': 'bar',
                'data': {
                    'labels': ['No data'],
                    'datasets': [{'label': 'Number of MRs', 'data': [0]}],
                },
                'options': {
                    'title': 'Lead Time Distribution',
                    'xLabel': 'Lead Time (hours)',
                    'yLabel': 'Number of MRs',
                    'isHistogram': True,
                    'histogram': {
                        'raw_values':     [],
                        'data_min':       0,
                        'data_max':       0,
                        'time_filter':    time_filter,
                        'filtered_count': 0,
                    },
                },
            }
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.set_xlabel('Lead Time (hours)')
            ax.set_ylabel('Number of MRs')
            ax.set_title('Lead Time Distribution – no data for selected period')
            ax.grid(axis='y', alpha=0.3)
            plt.tight_layout()
            chart_image = self._generate_matplotlib_image(fig)
            return {
                'chart_data': chart_data,
                'chart_image': chart_image,
                'statistics': {'count': 0, 'mean': 0, 'std': 0, 'min': 0,
                               'p25': 0, 'median': 0, 'p75': 0, 'max': 0},
            }

        values = df_filtered[lead_time_col].values
        n = len(values)
        data_min = float(values.min())
        data_max = float(values.max())
        data_range = data_max - data_min

        # ------------------------------------------------------------------
        # 3. Adaptive initial bin count – Freedman-Diaconis rule
        # ------------------------------------------------------------------
        q75, q25 = np.percentile(values, [75, 25])
        iqr = q75 - q25

        if iqr > 0 and data_range > 0:
            raw_width = 2.0 * iqr * (n ** (-1.0 / 3.0))
            # Round to a "nice" power-of-10 multiple
            magnitude = 10 ** np.floor(np.log10(raw_width))
            bin_width = np.ceil(raw_width / magnitude) * magnitude
            num_bins = max(10, min(80, int(np.ceil(data_range / bin_width))))
        else:
            # Sturges' rule fallback
            num_bins = max(10, min(50, int(np.ceil(np.log2(n) + 1))))

        # ------------------------------------------------------------------
        # 4. Compute display bins
        # ------------------------------------------------------------------
        hist_coarse, edges_coarse = np.histogram(values, bins=num_bins, range=(data_min, data_max))

        def _fmt_range(lo, hi):
            span = hi - lo
            decimals = 2 if span < 1 else (1 if span < 10 else 0)
            return f"{lo:.{decimals}f}–{hi:.{decimals}f}"

        coarse_labels = [_fmt_range(edges_coarse[i], edges_coarse[i + 1]) for i in range(num_bins)]

        chart_data = {
            'type': 'bar',
            'data': {
                'labels': coarse_labels,
                'datasets': [{
                    'label': 'Number of MRs',
                    'data': hist_coarse.tolist(),
                }],
            },
            'options': {
                'title': 'Lead Time Distribution',
                'xLabel': 'Lead Time (hours)',
                'yLabel': 'Number of MRs',
                'isHistogram': True,
                'histogram': {
                    'raw_values':       values.tolist(),
                    'data_min':         data_min,
                    'data_max':         data_max,
                    'time_filter':      time_filter,
                    'filtered_count':   int(n),
                },
            },
        }

        # ------------------------------------------------------------------
        # 5. Matplotlib fallback image
        # ------------------------------------------------------------------
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.bar(range(num_bins), hist_coarse, width=1, edgecolor='white', color='steelblue')
        tick_step = max(1, num_bins // 10)
        ax.set_xticks(range(0, num_bins, tick_step))
        ax.set_xticklabels(coarse_labels[::tick_step], rotation=45, ha='right')
        ax.set_xlabel('Lead Time (hours)')
        ax.set_ylabel('Number of MRs')
        ax.set_title('Lead Time Distribution')
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        chart_image = self._generate_matplotlib_image(fig)

        # ------------------------------------------------------------------
        # 6. Statistics
        # ------------------------------------------------------------------
        stats = df_filtered[lead_time_col].describe()
        statistics = {
            'count':  int(stats['count']),
            'mean':   float(stats['mean']),
            'std':    float(stats['std']),
            'min':    float(stats['min']),
            'p25':    float(stats['25%']),
            'median': float(stats['50%']),
            'p75':    float(stats['75%']),
            'max':    float(stats['max']),
        }

        return {
            'chart_data': chart_data,
            'chart_image': chart_image,
            'statistics': statistics,
        }
    
    def analyze_commits_distribution(self, df, analysis):
        """
        Analyze distribution of commits per MR
        """
        config = analysis.config
        commit_col = config.get('x_axis') or '#Commits'
        
        df = self._apply_config(df, config)
        
        # Ensure column exists
        if commit_col not in df.columns:
            raise ValueError(f"Column '{commit_col}' not found in dataset")
        
        # Convert to numeric
        df_copy = df.copy()
        df_copy[commit_col] = pd.to_numeric(df_copy[commit_col], errors='coerce').fillna(0).astype(int)
        
        commits_dist = df_copy[commit_col].value_counts().sort_index()
        
        # Limit to reasonable number of bars (top 20)
        if len(commits_dist) > 20:
            commits_dist = commits_dist.head(20)
        
        chart_data = {
            'type': analysis.chart_type or 'bar',
            'data': {
                'labels': [str(x) for x in commits_dist.index.tolist()],
                'datasets': [{
                    'label': 'Number of MRs',
                    'data': commits_dist.values.tolist(),
                }]
            },
            'options': {
                'title': 'Distribution of Commits per MR',
                'xLabel': 'Number of Commits',
                'yLabel': 'Number of MRs',
            }
        }
        
        # Generate matplotlib image
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(range(len(commits_dist)), commits_dist.values, color='steelblue')
        ax.set_xlabel('Number of Commits')
        ax.set_ylabel('Number of MRs')
        ax.set_title('Distribution of Commits per MR')
        ax.set_xticks(range(len(commits_dist)))
        ax.set_xticklabels([str(x) for x in commits_dist.index], rotation=45 if len(commits_dist) > 10 else 0)
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        chart_image = self._generate_matplotlib_image(fig)
        
        stats = df_copy[commit_col].describe()
        statistics = {
            'count': int(stats['count']),
            'mean': float(stats['mean']),
            'std': float(stats['std']),
            'min': int(stats['min']),
            'median': float(stats['50%']),
            'max': int(stats['max']),
        }
        
        return {
            'chart_data': chart_data,
            'chart_image': chart_image,
            'statistics': statistics
        }
    
    def analyze_commiters(self, df, analysis):
        """
        Analyze number of unique contributors per MR
        """
        config = analysis.config
        commiters_col = config.get('x_axis') or '#UniqueCommiters'
        
        df = self._apply_config(df, config)
        
        if commiters_col not in df.columns:
            raise ValueError(f"Column '{commiters_col}' not found in dataset")
        
        df_copy = df.copy()
        df_copy[commiters_col] = pd.to_numeric(df_copy[commiters_col], errors='coerce').fillna(0).astype(int)
        
        commiters_dist = df_copy[commiters_col].value_counts().sort_index()
        
        chart_data = {
            'type': analysis.chart_type or 'bar',
            'data': {
                'labels': [str(x) for x in commiters_dist.index.tolist()],
                'datasets': [{
                    'label': 'Number of MRs',
                    'data': commiters_dist.values.tolist(),
                }]
            },
            'options': {
                'title': 'Distribution of Unique Contributors per MR',
                'xLabel': 'Number of Contributors',
                'yLabel': 'Number of MRs',
            }
        }
        
        # Generate matplotlib image
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(range(len(commiters_dist)), commiters_dist.values, color='steelblue')
        ax.set_xlabel('Number of Contributors')
        ax.set_ylabel('Number of MRs')
        ax.set_title('Distribution of Unique Contributors per MR')
        ax.set_xticks(range(len(commiters_dist)))
        ax.set_xticklabels([str(x) for x in commiters_dist.index])
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        chart_image = self._generate_matplotlib_image(fig)
        
        stats = df_copy[commiters_col].describe()
        statistics = {
            'count': int(stats['count']),
            'mean': float(stats['mean']),
            'std': float(stats['std']),
            'min': int(stats['min']),
            'median': float(stats['50%']),
            'max': int(stats['max']),
        }
        
        return {
            'chart_data': chart_data,
            'chart_image': chart_image,
            'statistics': statistics
        }
    
    def analyze_top_commiters(self, df, analysis):
        """
        Top 10 committers ranked by number of MRs they contributed to.
        Parses the comma-separated 'Commiters' column.
        """
        config = analysis.config
        commiters_col = 'Commiters'

        df = self._apply_config(df, config)

        if commiters_col not in df.columns:
            raise ValueError(f"Column '{commiters_col}' not found in dataset")

        # Parse comma-separated committer names and count MR participation
        from collections import Counter
        counter = Counter()
        for val in df[commiters_col].dropna():
            names = [n.strip() for n in str(val).split(',') if n.strip()]
            counter.update(names)

        if not counter:
            raise ValueError("No committer data found")

        top10 = counter.most_common(10)
        labels = [name for name, _ in top10]
        values = [count for _, count in top10]

        chart_data = {
            'type': 'bar',
            'data': {
                'labels': labels,
                'datasets': [{
                    'label': 'MRs Contributed To',
                    'data': values,
                }]
            },
            'options': {
                'title': 'Top 10 Committers',
                'xLabel': 'Committer',
                'yLabel': 'Number of MRs',
            }
        }

        fig, ax = plt.subplots(figsize=(12, 6))
        bars = ax.barh(range(len(labels)), values, color='steelblue')
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels)
        ax.set_xlabel('Number of MRs')
        ax.set_title('Top 10 Committers')
        ax.invert_yaxis()
        ax.grid(axis='x', alpha=0.3)
        plt.tight_layout()

        chart_image = self._generate_matplotlib_image(fig)

        statistics = {
            'total_unique_commiters': len(counter),
            'top_commiter': labels[0] if labels else '',
            'top_commiter_mrs': values[0] if values else 0,
            'total_mrs': len(df),
        }

        return {
            'chart_data': chart_data,
            'chart_image': chart_image,
            'statistics': statistics
        }

    def analyze_top_authors(self, df, analysis):
        """
        Top 10 authors ranked by number of MRs they authored.
        Uses the 'Author' column.
        """
        config = analysis.config
        author_col = 'Author'

        df = self._apply_config(df, config)

        if author_col not in df.columns:
            raise ValueError(f"Column '{author_col}' not found in dataset. "
                             "This metric requires the Author column. "
                             "Re-collect your data to include it.")

        author_counts = df[author_col].dropna().astype(str).str.strip()
        author_counts = author_counts[author_counts != '']
        author_dist = author_counts.value_counts().head(10)

        if len(author_dist) == 0:
            raise ValueError("No author data found")

        labels = author_dist.index.tolist()
        values = author_dist.values.tolist()

        chart_data = {
            'type': 'bar',
            'data': {
                'labels': labels,
                'datasets': [{
                    'label': 'MRs Authored',
                    'data': values,
                }]
            },
            'options': {
                'title': 'Top 10 Authors',
                'xLabel': 'Author',
                'yLabel': 'Number of MRs',
            }
        }

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.barh(range(len(labels)), values, color='steelblue')
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels)
        ax.set_xlabel('Number of MRs')
        ax.set_title('Top 10 Authors')
        ax.invert_yaxis()
        ax.grid(axis='x', alpha=0.3)
        plt.tight_layout()

        chart_image = self._generate_matplotlib_image(fig)

        total_authors = df[author_col].dropna().nunique()
        statistics = {
            'total_unique_authors': int(total_authors),
            'top_author': labels[0] if labels else '',
            'top_author_mrs': values[0] if values else 0,
            'total_mrs': len(df),
        }

        return {
            'chart_data': chart_data,
            'chart_image': chart_image,
            'statistics': statistics
        }

    def analyze_top_reviewers(self, df, analysis):
        """
        Top 10 reviewers ranked by number of MRs they reviewed.
        Parses the comma-separated 'Reviewers' column.
        """
        config = analysis.config
        reviewers_col = 'Reviewers'

        df = self._apply_config(df, config)

        if reviewers_col not in df.columns:
            raise ValueError(f"Column '{reviewers_col}' not found in dataset. "
                             "This metric requires the Reviewers column. "
                             "Re-collect your data to include it.")

        from collections import Counter
        counter = Counter()
        for val in df[reviewers_col].dropna():
            names = [n.strip() for n in str(val).split(',') if n.strip()]
            counter.update(names)

        if not counter:
            raise ValueError("No reviewer data found")

        top10 = counter.most_common(10)
        labels = [name for name, _ in top10]
        values = [count for _, count in top10]

        chart_data = {
            'type': 'bar',
            'data': {
                'labels': labels,
                'datasets': [{
                    'label': 'MRs Reviewed',
                    'data': values,
                }]
            },
            'options': {
                'title': 'Top 10 Reviewers',
                'xLabel': 'Reviewer',
                'yLabel': 'Number of MRs',
            }
        }

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.barh(range(len(labels)), values, color='steelblue')
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels)
        ax.set_xlabel('Number of MRs')
        ax.set_title('Top 10 Reviewers')
        ax.invert_yaxis()
        ax.grid(axis='x', alpha=0.3)
        plt.tight_layout()

        chart_image = self._generate_matplotlib_image(fig)

        statistics = {
            'total_unique_reviewers': len(counter),
            'top_reviewer': labels[0] if labels else '',
            'top_reviewer_mrs': values[0] if values else 0,
            'total_mrs': len(df),
        }

        return {
            'chart_data': chart_data,
            'chart_image': chart_image,
            'statistics': statistics
        }

    def analyze_custom_chart(self, df, analysis):
        """
        Generic function for custom X/Y axis charts
        """
        config = analysis.config
        x_axis = config.get('x_axis')
        y_axis = config.get('y_axis')
        aggregation = config.get('aggregation', 'sum')
        
        if not x_axis or not y_axis:
            raise ValueError("x_axis and y_axis must be specified for custom charts")
        
        df = self._apply_config(df, config)
        
        # Handle different chart types
        if analysis.chart_type == 'scatter':
            chart_data = {
                'type': 'scatter',
                'data': {
                    'datasets': [{
                        'label': f'{y_axis} vs {x_axis}',
                        'data': [
                            {'x': float(x), 'y': float(y)}
                            for x, y in zip(df[x_axis], df[y_axis])
                            if pd.notna(x) and pd.notna(y)
                        ]
                    }]
                },
                'options': {
                    'title': f'{y_axis} vs {x_axis}',
                    'xLabel': x_axis,
                    'yLabel': y_axis,
                }
            }
            
            # Generate matplotlib image
            fig, ax = plt.subplots(figsize=(10, 8))
            ax.scatter(df[x_axis], df[y_axis], alpha=0.5)
            ax.set_xlabel(x_axis)
            ax.set_ylabel(y_axis)
            ax.set_title(f'{y_axis} vs {x_axis}')
            plt.tight_layout()
            
            chart_image = self._generate_matplotlib_image(fig)
            
            # Calculate correlation
            correlation = df[[x_axis, y_axis]].corr().iloc[0, 1]
            statistics = {
                'correlation': float(correlation) if pd.notna(correlation) else 0,
                'x_mean': round(float(df[x_axis].mean()), 2) if pd.notna(df[x_axis].mean()) else 0,
                'y_mean': round(float(df[y_axis].mean()), 2) if pd.notna(df[y_axis].mean()) else 0,
                'data_points': len(df),
            }
            
        else:
            # For bar/line charts, group by x_axis and aggregate y_axis
            if aggregation == 'sum':
                result = df.groupby(x_axis)[y_axis].sum()
            elif aggregation == 'mean':
                result = df.groupby(x_axis)[y_axis].mean()
            elif aggregation == 'median':
                result = df.groupby(x_axis)[y_axis].median()
            elif aggregation == 'count':
                result = df.groupby(x_axis).size()
            else:
                result = df.groupby(x_axis)[y_axis].sum()
            
            chart_data = {
                'type': analysis.chart_type,
                'data': {
                    'labels': [str(x) for x in result.index],
                    'datasets': [{
                        'label': f'{y_axis} ({aggregation})',
                        'data': result.values.tolist(),
                    }]
                },
                'options': {
                    'title': f'{y_axis} by {x_axis} ({aggregation})',
                    'xLabel': x_axis,
                    'yLabel': f'{y_axis} ({aggregation})',
                }
            }
            
            # Generate matplotlib image
            fig, ax = plt.subplots(figsize=(12, 6))
            if analysis.chart_type == 'line':
                ax.plot(range(len(result)), result.values, marker='o')
            else:  # bar
                ax.bar(range(len(result)), result.values)
            ax.set_xlabel(x_axis)
            ax.set_ylabel(f'{y_axis} ({aggregation})')
            ax.set_title(chart_data['options']['title'])
            ax.set_xticks(range(len(result)))
            ax.set_xticklabels([str(x) for x in result.index], rotation=45, ha='right')
            plt.tight_layout()
            
            chart_image = self._generate_matplotlib_image(fig)
            
            statistics = result.describe().to_dict()
        
        return {
            'chart_data': chart_data,
            'chart_image': chart_image,
            'statistics': statistics
        }
    
    def analyze_commit_time(self, df, analysis):
        """
        Analyze commit time distribution - when do commits happen
        """
        config = analysis.config
        date_col = config.get('x_axis') or 'Creation_Date'
        
        df = self._apply_config(df, config)
        df_copy = df.copy()
        
        if not pd.api.types.is_datetime64_any_dtype(df_copy[date_col]):
            df_copy[date_col] = pd.to_datetime(df_copy[date_col], errors='coerce', format='mixed')
        
        df_copy = df_copy.dropna(subset=[date_col])
        
        # Extract hour of day
        df_copy['hour'] = df_copy[date_col].dt.hour
        hour_dist = df_copy['hour'].value_counts().sort_index()
        
        # Ensure all 24 hours are represented
        all_hours = pd.Series(0, index=range(24))
        hour_dist = hour_dist.add(all_hours, fill_value=0).astype(int)
        
        chart_data = {
            'type': 'bar',
            'data': {
                'labels': [f"{h}:00" for h in range(24)],
                'datasets': [{
                    'label': 'Number of MRs',
                    'data': hour_dist.values.tolist(),
                }]
            },
            'options': {
                'title': 'MR Creation by Hour of Day',
                'xLabel': 'Hour of Day',
                'yLabel': 'Number of MRs',
            }
        }
        
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.bar(range(24), hour_dist.values, color='steelblue')
        ax.set_xlabel('Hour of Day')
        ax.set_ylabel('Number of MRs')
        ax.set_title('MR Creation by Hour of Day')
        ax.set_xticks(range(24))
        ax.set_xticklabels([f"{h}:00" for h in range(24)], rotation=45)
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        chart_image = self._generate_matplotlib_image(fig)
        
        # Find peak hours
        peak_hour = hour_dist.idxmax()
        statistics = {
            'peak_hour': f"{peak_hour}:00",
            'peak_count': int(hour_dist.max()),
            'total_mrs': int(hour_dist.sum()),
        }
        
        return {
            'chart_data': chart_data,
            'chart_image': chart_image,
            'statistics': statistics
        }
    
    def analyze_code_churn(self, df, analysis):
        """
        Analyze code churn (additions + deletions) over time
        """
        config = analysis.config
        date_col = config.get('x_axis') or 'Creation_Date'
        freq = config.get('time_aggregation') or 'M'
        
        df = self._apply_config(df, config)
        df_copy = df.copy()
        
        # Determine which addition/deletion columns to use.
        # Prefer per-MR columns (additions/deletions) for meaningful time-series.
        # Fall back to churn_addition/churn_deletions if per-MR columns are absent.
        if 'additions' in df_copy.columns and 'deletions' in df_copy.columns:
            add_col = 'additions'
            del_col = 'deletions'
        elif 'churn_addition' in df_copy.columns and 'churn_deletions' in df_copy.columns:
            add_col = 'churn_addition'
            del_col = 'churn_deletions'
        else:
            raise ValueError("Required columns for churn analysis not found. Need (additions, deletions) or (churn_addition, churn_deletions).")
        
        if not pd.api.types.is_datetime64_any_dtype(df_copy[date_col]):
            df_copy[date_col] = pd.to_datetime(df_copy[date_col], errors='coerce', format='mixed')
        
        df_copy = df_copy.dropna(subset=[date_col])
        df_copy[add_col] = pd.to_numeric(df_copy[add_col], errors='coerce').fillna(0)
        df_copy[del_col] = pd.to_numeric(df_copy[del_col], errors='coerce').fillna(0)
        df_copy['total_churn'] = df_copy[add_col] + df_copy[del_col]
        df_copy['period'] = df_copy[date_col].dt.to_period(freq)
        
        churn_by_period = df_copy.groupby('period').agg({
            add_col: 'sum',
            del_col: 'sum',
            'total_churn': 'sum'
        }).sort_index()
        
        labels = self._format_date_labels(churn_by_period.index)
        
        chart_data = {
            'type': 'bar',
            'data': {
                'labels': labels,
                'datasets': [
                    {
                        'label': 'Additions',
                        'data': churn_by_period[add_col].values.tolist(),
                        'backgroundColor': 'rgba(34, 197, 94, 0.7)',
                    },
                    {
                        'label': 'Deletions',
                        'data': churn_by_period[del_col].values.tolist(),
                        'backgroundColor': 'rgba(239, 68, 68, 0.7)',
                    }
                ]
            },
            'options': {
                'title': 'Code Churn Over Time',
                'xLabel': 'Period',
                'yLabel': 'Lines Changed',
            }
        }
        
        fig, ax = plt.subplots(figsize=(12, 6))
        x = range(len(churn_by_period))
        width = 0.35
        ax.bar([i - width/2 for i in x], churn_by_period[add_col].values, width, label='Additions', color='green', alpha=0.7)
        ax.bar([i + width/2 for i in x], churn_by_period[del_col].values, width, label='Deletions', color='red', alpha=0.7)
        ax.set_xlabel('Period')
        ax.set_ylabel('Lines Changed')
        ax.set_title('Code Churn Over Time')
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        chart_image = self._generate_matplotlib_image(fig)
        
        statistics = {
            'total_additions': int(churn_by_period[add_col].sum()),
            'total_deletions': int(churn_by_period[del_col].sum()),
            'total_churn': int(churn_by_period['total_churn'].sum()),
            'avg_churn_per_period': float(churn_by_period['total_churn'].mean()),
        }
        
        return {
            'chart_data': chart_data,
            'chart_image': chart_image,
            'statistics': statistics
        }
    
    def analyze_churn_scatter(self, df, analysis):
        """
        Scatter plot of additions vs deletions per MR
        """
        config = analysis.config
        
        df = self._apply_config(df, config)
        df_copy = df.copy()
        
        # Prefer per-MR columns; fall back to churn columns
        if 'additions' in df_copy.columns and 'deletions' in df_copy.columns:
            add_col = 'additions'
            del_col = 'deletions'
        elif 'churn_addition' in df_copy.columns and 'churn_deletions' in df_copy.columns:
            add_col = 'churn_addition'
            del_col = 'churn_deletions'
        else:
            raise ValueError("Required columns not found. Need (additions, deletions) or (churn_addition, churn_deletions).")
        
        df_copy[add_col] = pd.to_numeric(df_copy[add_col], errors='coerce').fillna(0)
        df_copy[del_col] = pd.to_numeric(df_copy[del_col], errors='coerce').fillna(0)
        
        # Filter out outliers for better visualization
        q99_add = df_copy[add_col].quantile(0.99)
        q99_del = df_copy[del_col].quantile(0.99)
        df_filtered = df_copy[(df_copy[add_col] <= q99_add) & (df_copy[del_col] <= q99_del)]
        
        chart_data = {
            'type': 'scatter',
            'data': {
                'datasets': [{
                    'label': 'MRs',
                    'data': [
                        {'x': float(x), 'y': float(y)}
                        for x, y in zip(df_filtered[add_col], df_filtered[del_col])
                    ]
                }]
            },
            'options': {
                'title': 'Additions vs Deletions per MR',
                'xLabel': 'Additions',
                'yLabel': 'Deletions',
            }
        }
        
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.scatter(df_filtered[add_col], df_filtered[del_col], alpha=0.5, c='steelblue')
        ax.set_xlabel('Additions')
        ax.set_ylabel('Deletions')
        ax.set_title('Additions vs Deletions per MR')
        ax.grid(alpha=0.3)
        plt.tight_layout()
        
        chart_image = self._generate_matplotlib_image(fig)
        
        correlation = df_copy[[add_col, del_col]].corr().iloc[0, 1]
        statistics = {
            'correlation': float(correlation) if pd.notna(correlation) else 0,
            'total_mrs': len(df_copy),
            'avg_additions': float(df_copy[add_col].mean()),
            'avg_deletions': float(df_copy[del_col].mean()),
        }
        
        return {
            'chart_data': chart_data,
            'chart_image': chart_image,
            'statistics': statistics
        }
    
    def analyze_mr_size(self, df, analysis):
        """
        Analyze MR size distribution (total lines changed)
        """
        config = analysis.config
        
        df = self._apply_config(df, config)
        df_copy = df.copy()
        
        # Use initial_mr_size directly if available (preferred)
        if 'initial_mr_size' in df_copy.columns:
            df_copy['mr_size'] = pd.to_numeric(df_copy['initial_mr_size'], errors='coerce').fillna(0)
        else:
            # Fall back to computing from additions + deletions
            if 'additions' in df_copy.columns and 'deletions' in df_copy.columns:
                add_col, del_col = 'additions', 'deletions'
            elif 'churn_addition' in df_copy.columns and 'churn_deletions' in df_copy.columns:
                add_col, del_col = 'churn_addition', 'churn_deletions'
            else:
                raise ValueError("Required columns for MR size analysis not found.")
            df_copy[add_col] = pd.to_numeric(df_copy[add_col], errors='coerce').fillna(0)
            df_copy[del_col] = pd.to_numeric(df_copy[del_col], errors='coerce').fillna(0)
            df_copy['mr_size'] = df_copy[add_col] + df_copy[del_col]
        
        # Filter out extreme outliers
        q99 = df_copy['mr_size'].quantile(0.99)
        df_filtered = df_copy[df_copy['mr_size'] <= q99]
        
        values = df_filtered['mr_size'].values
        hist_values, bin_edges = np.histogram(values, bins=30)
        bin_labels = [f"{int(bin_edges[i])}-{int(bin_edges[i+1])}" for i in range(len(bin_edges)-1)]
        
        chart_data = {
            'type': 'bar',
            'data': {
                'labels': bin_labels,
                'datasets': [{
                    'label': 'Number of MRs',
                    'data': hist_values.tolist(),
                }]
            },
            'options': {
                'title': 'MR Size Distribution (Lines Changed)',
                'xLabel': 'MR Size (lines)',
                'yLabel': 'Number of MRs',
            }
        }
        
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.hist(values, bins=30, edgecolor='white', color='steelblue')
        ax.set_xlabel('MR Size (lines)')
        ax.set_ylabel('Number of MRs')
        ax.set_title('MR Size Distribution (Lines Changed)')
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        chart_image = self._generate_matplotlib_image(fig)
        
        stats = df_copy['mr_size'].describe()
        statistics = {
            'count': int(stats['count']),
            'mean': float(stats['mean']),
            'median': float(stats['50%']),
            'std': float(stats['std']),
            'min': int(stats['min']),
            'max': int(stats['max']),
        }
        
        return {
            'chart_data': chart_data,
            'chart_image': chart_image,
            'statistics': statistics
        }
    
    def analyze_discussions(self, df, analysis):
        """
        Analyze discussions count per MR
        """
        config = analysis.config
        discussions_col = config.get('x_axis') or '#Discussions'
        
        df = self._apply_config(df, config)
        
        if discussions_col not in df.columns:
            raise ValueError(f"Column '{discussions_col}' not found in dataset")
        
        df_copy = df.copy()
        df_copy[discussions_col] = pd.to_numeric(df_copy[discussions_col], errors='coerce').fillna(0).astype(int)
        
        disc_dist = df_copy[discussions_col].value_counts().sort_index()
        
        # Limit to top 15 for readability
        if len(disc_dist) > 15:
            disc_dist = disc_dist.head(15)
        
        chart_data = {
            'type': 'bar',
            'data': {
                'labels': [str(x) for x in disc_dist.index.tolist()],
                'datasets': [{
                    'label': 'Number of MRs',
                    'data': disc_dist.values.tolist(),
                }]
            },
            'options': {
                'title': 'Distribution of Discussions per MR',
                'xLabel': 'Number of Discussions',
                'yLabel': 'Number of MRs',
            }
        }
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(range(len(disc_dist)), disc_dist.values, color='steelblue')
        ax.set_xlabel('Number of Discussions')
        ax.set_ylabel('Number of MRs')
        ax.set_title('Distribution of Discussions per MR')
        ax.set_xticks(range(len(disc_dist)))
        ax.set_xticklabels([str(x) for x in disc_dist.index])
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        chart_image = self._generate_matplotlib_image(fig)
        
        stats = df_copy[discussions_col].describe()
        statistics = {
            'count': int(stats['count']),
            'mean': float(stats['mean']),
            'median': float(stats['50%']),
            'max': int(stats['max']),
            'mrs_with_discussions': int((df_copy[discussions_col] > 0).sum()),
        }
        
        return {
            'chart_data': chart_data,
            'chart_image': chart_image,
            'statistics': statistics
        }
    
    def analyze_collaboration_metrics(self, df, analysis):
        """
        Analyze collaboration metrics: people, reviewers, commiters, discussionners
        """
        config = analysis.config
        
        df = self._apply_config(df, config)
        df_copy = df.copy()
        
        # Define collaboration columns
        collab_cols = ['#people', '#reviewers', '#commiters', '#discussionners']
        available_cols = [c for c in collab_cols if c in df_copy.columns]
        
        if not available_cols:
            raise ValueError("No collaboration columns found in dataset")
        
        # Calculate means
        means = {}
        for col in available_cols:
            df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce').fillna(0)
            means[col.replace('#', '')] = float(df_copy[col].mean())
        
        labels = list(means.keys())
        values = list(means.values())
        
        chart_data = {
            'type': 'bar',
            'data': {
                'labels': labels,
                'datasets': [{
                    'label': 'Average per MR',
                    'data': values,
                }]
            },
            'options': {
                'title': 'Average Collaboration Metrics per MR',
                'xLabel': 'Metric',
                'yLabel': 'Average Count',
            }
        }
        
        fig, ax = plt.subplots(figsize=(10, 6))
        colors = ['#3b82f6', '#f59e0b', '#10b981', '#8b5cf6']
        ax.bar(labels, values, color=colors[:len(labels)])
        ax.set_xlabel('Metric')
        ax.set_ylabel('Average Count')
        ax.set_title('Average Collaboration Metrics per MR')
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        chart_image = self._generate_matplotlib_image(fig)
        
        statistics = {
            'total_mrs': len(df_copy),
            'avg_people': round(means.get('people', 0), 2),
            'avg_reviewers': round(means.get('reviewers', 0), 2),
            'avg_commiters': round(means.get('commiters', 0), 2),
            'avg_discussionners': round(means.get('discussionners', 0), 2),
        }
        
        return {
            'chart_data': chart_data,
            'chart_image': chart_image,
            'statistics': statistics
        }
    
    def analyze_comments(self, df, analysis):
        """
        Analyze comments distribution per MR
        """
        config = analysis.config
        comments_col = config.get('x_axis') or 'comments'
        
        df = self._apply_config(df, config)
        
        if comments_col not in df.columns:
            raise ValueError(f"Column '{comments_col}' not found in dataset")
        
        df_copy = df.copy()
        df_copy[comments_col] = pd.to_numeric(df_copy[comments_col], errors='coerce').fillna(0).astype(int)
        
        comments_dist = df_copy[comments_col].value_counts().sort_index()
        
        # Limit for readability
        if len(comments_dist) > 20:
            comments_dist = comments_dist.head(20)
        
        chart_data = {
            'type': 'bar',
            'data': {
                'labels': [str(x) for x in comments_dist.index.tolist()],
                'datasets': [{
                    'label': 'Number of MRs',
                    'data': comments_dist.values.tolist(),
                }]
            },
            'options': {
                'title': 'Distribution of Comments per MR',
                'xLabel': 'Number of Comments',
                'yLabel': 'Number of MRs',
            }
        }
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(range(len(comments_dist)), comments_dist.values, color='steelblue')
        ax.set_xlabel('Number of Comments')
        ax.set_ylabel('Number of MRs')
        ax.set_title('Distribution of Comments per MR')
        ax.set_xticks(range(len(comments_dist)))
        ax.set_xticklabels([str(x) for x in comments_dist.index])
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        chart_image = self._generate_matplotlib_image(fig)
        
        stats = df_copy[comments_col].describe()
        statistics = {
            'count': int(stats['count']),
            'mean': float(stats['mean']),
            'median': float(stats['50%']),
            'max': int(stats['max']),
            'total_comments': int(df_copy[comments_col].sum()),
        }
        
        return {
            'chart_data': chart_data,
            'chart_image': chart_image,
            'statistics': statistics
        }
    
    def analyze_files_modified(self, df, analysis):
        """
        Analyze number of files modified per MR
        """
        config = analysis.config
        files_col = config.get('x_axis') or 'modified_files'
        
        df = self._apply_config(df, config)
        
        if files_col not in df.columns:
            raise ValueError(f"Column '{files_col}' not found in dataset")
        
        df_copy = df.copy()
        df_copy[files_col] = pd.to_numeric(df_copy[files_col], errors='coerce').fillna(0).astype(int)
        
        files_dist = df_copy[files_col].value_counts().sort_index()
        
        # Limit for readability
        if len(files_dist) > 20:
            files_dist = files_dist.head(20)
        
        chart_data = {
            'type': 'bar',
            'data': {
                'labels': [str(x) for x in files_dist.index.tolist()],
                'datasets': [{
                    'label': 'Number of MRs',
                    'data': files_dist.values.tolist(),
                }]
            },
            'options': {
                'title': 'Distribution of Files Modified per MR',
                'xLabel': 'Number of Files',
                'yLabel': 'Number of MRs',
            }
        }
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(range(len(files_dist)), files_dist.values, color='steelblue')
        ax.set_xlabel('Number of Files')
        ax.set_ylabel('Number of MRs')
        ax.set_title('Distribution of Files Modified per MR')
        ax.set_xticks(range(len(files_dist)))
        ax.set_xticklabels([str(x) for x in files_dist.index])
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        chart_image = self._generate_matplotlib_image(fig)
        
        stats = df_copy[files_col].describe()
        statistics = {
            'count': int(stats['count']),
            'mean': float(stats['mean']),
            'median': float(stats['50%']),
            'max': int(stats['max']),
        }
        
        return {
            'chart_data': chart_data,
            'chart_image': chart_image,
            'statistics': statistics
        }
    
    def analyze_filetypes_distribution(self, df, analysis):
        """
        Analyze distribution of file types in MRs
        """
        config = analysis.config
        filetypes_col = config.get('x_axis') or 'filetypes'
        
        df = self._apply_config(df, config)
        
        if filetypes_col not in df.columns:
            raise ValueError(f"Column '{filetypes_col}' not found in dataset")
        
        df_copy = df.copy()
        df_copy[filetypes_col] = pd.to_numeric(df_copy[filetypes_col], errors='coerce').fillna(0).astype(int)
        
        filetypes_dist = df_copy[filetypes_col].value_counts().sort_index()
        
        if len(filetypes_dist) > 15:
            filetypes_dist = filetypes_dist.head(15)
        
        chart_data = {
            'type': 'bar',
            'data': {
                'labels': [str(x) for x in filetypes_dist.index.tolist()],
                'datasets': [{
                    'label': 'Number of MRs',
                    'data': filetypes_dist.values.tolist(),
                }]
            },
            'options': {
                'title': 'Distribution of File Types per MR',
                'xLabel': 'Number of File Types',
                'yLabel': 'Number of MRs',
            }
        }
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(range(len(filetypes_dist)), filetypes_dist.values, color='steelblue')
        ax.set_xlabel('Number of File Types')
        ax.set_ylabel('Number of MRs')
        ax.set_title('Distribution of File Types per MR')
        ax.set_xticks(range(len(filetypes_dist)))
        ax.set_xticklabels([str(x) for x in filetypes_dist.index])
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        chart_image = self._generate_matplotlib_image(fig)
        
        stats = df_copy[filetypes_col].describe()
        statistics = {
            'count': int(stats['count']),
            'mean': float(stats['mean']),
            'median': float(stats['50%']),
            'max': int(stats['max']),
        }
        
        return {
            'chart_data': chart_data,
            'chart_image': chart_image,
            'statistics': statistics
        }
    
    def analyze_entropy(self, df, analysis):
        """
        Analyze historical entropy distribution
        """
        config = analysis.config
        entropy_col = config.get('x_axis') or 'hist_entropy'
        
        df = self._apply_config(df, config)
        
        if entropy_col not in df.columns:
            raise ValueError(f"Column '{entropy_col}' not found in dataset")
        
        df_copy = df.copy()
        df_copy[entropy_col] = pd.to_numeric(df_copy[entropy_col], errors='coerce')
        df_filtered = df_copy.dropna(subset=[entropy_col])
        
        values = df_filtered[entropy_col].values
        hist_values, bin_edges = np.histogram(values, bins=30)
        bin_labels = [f"{bin_edges[i]:.2f}" for i in range(len(bin_edges)-1)]
        
        chart_data = {
            'type': 'bar',
            'data': {
                'labels': bin_labels,
                'datasets': [{
                    'label': 'Frequency',
                    'data': hist_values.tolist(),
                }]
            },
            'options': {
                'title': 'Historical Entropy Distribution',
                'xLabel': 'Entropy',
                'yLabel': 'Number of MRs',
            }
        }
        
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.hist(values, bins=30, edgecolor='white', color='steelblue')
        ax.set_xlabel('Entropy')
        ax.set_ylabel('Number of MRs')
        ax.set_title('Historical Entropy Distribution')
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        chart_image = self._generate_matplotlib_image(fig)
        
        stats = df_filtered[entropy_col].describe()
        statistics = {
            'count': int(stats['count']),
            'mean': float(stats['mean']),
            'median': float(stats['50%']),
            'std': float(stats['std']),
            'min': float(stats['min']),
            'max': float(stats['max']),
        }
        
        return {
            'chart_data': chart_data,
            'chart_image': chart_image,
            'statistics': statistics
        }
    
    def analyze_state_distribution(self, df, analysis):
        """
        Analyze distribution of MR states (opened, merged, closed)
        """
        config = analysis.config
        state_col = config.get('x_axis') or 'state'
        
        df = self._apply_config(df, config)
        
        if state_col not in df.columns:
            raise ValueError(f"Column '{state_col}' not found in dataset")
        
        state_dist = df[state_col].value_counts()
        
        chart_data = {
            'type': 'pie',
            'data': {
                'labels': state_dist.index.tolist(),
                'datasets': [{
                    'data': state_dist.values.tolist(),
                }]
            },
            'options': {
                'title': 'MR State Distribution',
            }
        }
        
        fig, ax = plt.subplots(figsize=(10, 8))
        colors = ['#3b82f6', '#10b981', '#ef4444', '#f59e0b']
        ax.pie(state_dist.values, labels=state_dist.index, autopct='%1.1f%%', 
               colors=colors[:len(state_dist)], startangle=90)
        ax.set_title('MR State Distribution')
        plt.tight_layout()
        
        chart_image = self._generate_matplotlib_image(fig)
        
        # Flatten state counts into top-level statistics
        flat_stats = {'total_mrs': int(state_dist.sum())}
        for state_name, count in state_dist.items():
            flat_stats[f'{state_name}_count'] = int(count)
        
        statistics = flat_stats
        
        return {
            'chart_data': chart_data,
            'chart_image': chart_image,
            'statistics': statistics
        }
    
    def analyze_rework(self, df, analysis):
        """
        Analyze rework size distribution with adaptive binning and time-based filtering.

        Config params:
          x_axis       – column name for rework (default: 'rework_size')
          time_filter  – 'all' | 'daily' | 'weekly' | 'monthly'
                         Filters rows by Creation_Date before computing the histogram.
        """
        config = analysis.config
        rework_col = config.get('x_axis') or 'rework_size'
        time_filter = config.get('time_filter', 'all')
        date_col = 'Creation_Date'

        df = self._apply_config(df, config)
        df_filtered = df.copy()

        # ------------------------------------------------------------------
        # 1. Time-based filtering on Creation_Date
        #    Use the dataset's own max date as the reference point so that
        #    historical datasets produce meaningful results.
        # ------------------------------------------------------------------
        if time_filter != 'all' and date_col in df_filtered.columns:
            if not pd.api.types.is_datetime64_any_dtype(df_filtered[date_col]):
                df_filtered[date_col] = pd.to_datetime(df_filtered[date_col], errors='coerce')
            if df_filtered[date_col].dt.tz is not None:
                df_filtered[date_col] = df_filtered[date_col].dt.tz_localize(None)
            max_date = df_filtered[date_col].dropna().max()
            if pd.notna(max_date):
                days_map = {'daily': 1, 'weekly': 7, 'monthly': 30}
                days = days_map.get(time_filter)
                if days:
                    cutoff = max_date - pd.Timedelta(days=days)
                    df_filtered = df_filtered[df_filtered[date_col] >= cutoff]

        # ------------------------------------------------------------------
        # 2. Clean the rework column
        # ------------------------------------------------------------------
        if rework_col not in df_filtered.columns:
            raise ValueError(f"Column '{rework_col}' not found in dataset")

        df_filtered[rework_col] = pd.to_numeric(df_filtered[rework_col], errors='coerce').fillna(0)

        # Keep stats on full set before filtering zeros
        all_stats = df_filtered[rework_col].describe()
        mrs_with_rework = int((df_filtered[rework_col] > 0).sum())
        mrs_without_rework = int((df_filtered[rework_col] == 0).sum())

        # Filter out zeros for better visualization
        df_filtered = df_filtered[df_filtered[rework_col] > 0]

        if len(df_filtered) == 0:
            # All zeros – still return isHistogram so filter buttons stay visible
            chart_data = {
                'type': 'bar',
                'data': {
                    'labels': ['0'],
                    'datasets': [{'label': 'Number of MRs', 'data': [mrs_without_rework]}],
                },
                'options': {
                    'title': 'Rework Size Distribution',
                    'xLabel': 'Rework Size',
                    'yLabel': 'Number of MRs',
                    'isHistogram': True,
                    'histogram': {
                        'raw_values':     [],
                        'data_min':       0,
                        'data_max':       0,
                        'time_filter':    time_filter,
                        'filtered_count': 0,
                    },
                },
            }
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.bar([0], [mrs_without_rework], color='steelblue')
            ax.set_xlabel('Rework Size')
            ax.set_ylabel('Number of MRs')
            ax.set_title('Rework Size Distribution')
            ax.grid(axis='y', alpha=0.3)
            plt.tight_layout()
            chart_image = self._generate_matplotlib_image(fig)

            return {
                'chart_data': chart_data,
                'chart_image': chart_image,
                'statistics': {
                    'count': int(all_stats['count']),
                    'mean': float(all_stats['mean']),
                    'median': float(all_stats['50%']),
                    'max': float(all_stats['max']),
                    'mrs_with_rework': mrs_with_rework,
                    'mrs_without_rework': mrs_without_rework,
                },
            }

        # Filter outliers (> 99th percentile)
        q99 = df_filtered[rework_col].quantile(0.99)
        df_filtered = df_filtered[df_filtered[rework_col] <= q99]

        values = df_filtered[rework_col].values
        n = len(values)
        data_min = float(values.min())
        data_max = float(values.max())
        data_range = data_max - data_min

        # ------------------------------------------------------------------
        # 3. Adaptive bin count – Freedman-Diaconis rule
        # ------------------------------------------------------------------
        q75, q25 = np.percentile(values, [75, 25])
        iqr = q75 - q25

        if iqr > 0 and data_range > 0:
            raw_width = 2.0 * iqr * (n ** (-1.0 / 3.0))
            magnitude = 10 ** np.floor(np.log10(raw_width))
            bin_width = np.ceil(raw_width / magnitude) * magnitude
            num_bins = max(10, min(80, int(np.ceil(data_range / bin_width))))
        else:
            num_bins = max(10, min(50, int(np.ceil(np.log2(n) + 1))))

        # ------------------------------------------------------------------
        # 4. Compute display bins
        # ------------------------------------------------------------------
        hist_values, edges = np.histogram(values, bins=num_bins, range=(data_min, data_max))

        def _fmt_range(lo, hi):
            span = hi - lo
            decimals = 2 if span < 1 else (1 if span < 10 else 0)
            return f"{lo:.{decimals}f}–{hi:.{decimals}f}"

        bin_labels = [_fmt_range(edges[i], edges[i + 1]) for i in range(num_bins)]

        chart_data = {
            'type': 'bar',
            'data': {
                'labels': bin_labels,
                'datasets': [{
                    'label': 'Number of MRs',
                    'data': hist_values.tolist(),
                }],
            },
            'options': {
                'title': 'Rework Size Distribution (non-zero only)',
                'xLabel': 'Rework Size',
                'yLabel': 'Number of MRs',
                'isHistogram': True,
                'histogram': {
                    'raw_values':     values.tolist(),
                    'data_min':       data_min,
                    'data_max':       data_max,
                    'time_filter':    time_filter,
                    'filtered_count': int(n),
                },
            },
        }

        # ------------------------------------------------------------------
        # 5. Matplotlib fallback image
        # ------------------------------------------------------------------
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.bar(range(num_bins), hist_values, width=1, edgecolor='white', color='steelblue')
        tick_step = max(1, num_bins // 10)
        ax.set_xticks(range(0, num_bins, tick_step))
        ax.set_xticklabels(bin_labels[::tick_step], rotation=45, ha='right')
        ax.set_xlabel('Rework Size')
        ax.set_ylabel('Number of MRs')
        ax.set_title('Rework Size Distribution')
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        chart_image = self._generate_matplotlib_image(fig)

        # ------------------------------------------------------------------
        # 6. Statistics
        # ------------------------------------------------------------------
        statistics = {
            'count': int(all_stats['count']),
            'mean': float(all_stats['mean']),
            'median': float(all_stats['50%']),
            'max': float(all_stats['max']),
            'mrs_with_rework': mrs_with_rework,
            'mrs_without_rework': mrs_without_rework,
        }

        return {
            'chart_data': chart_data,
            'chart_image': chart_image,
            'statistics': statistics,
        }
    
    def analyze_correlation_matrix(self, df, analysis):
        """
        Analyze correlation between numeric columns.
        Auto-detects numeric columns from the dataset instead of hardcoding.
        """
        config = analysis.config
        
        df = self._apply_config(df, config)
        
        # Handle Lead_Time 'open' values BEFORE numeric conversion
        df_work = df.copy()
        if 'Lead_Time' in df_work.columns:
            df_work = df_work[df_work['Lead_Time'].astype(str) != 'open']
        
        # Skip columns that are IDs or non-numeric metadata
        skip_cols = {'Project_ID', 'MR_ID', 'Commiters', 'state', 'filetypes',
                     'Creation_Date', 'created_at', 'updated_at', 'merged_at', 'closed_at'}
        
        # Auto-detect numeric columns
        available_cols = []
        for col in df_work.columns:
            if col in skip_cols:
                continue
            numeric_vals = pd.to_numeric(df_work[col], errors='coerce')
            # Only include columns where at least 50% of values are numeric
            if numeric_vals.notna().sum() / max(len(df_work), 1) > 0.5:
                available_cols.append(col)
        
        if len(available_cols) < 2:
            raise ValueError("Not enough numeric columns for correlation analysis")
        
        df_copy = df_work[available_cols].copy()
        for col in available_cols:
            df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce')
        
        # Drop rows where any value is NaN
        df_copy = df_copy.dropna()
        
        if len(df_copy) < 2:
            raise ValueError("Not enough data rows for correlation analysis after filtering")
        
        # Remove zero-variance columns (they produce NaN correlations)
        non_const_cols = [c for c in df_copy.columns if df_copy[c].nunique() > 1]
        if len(non_const_cols) < 2:
            raise ValueError("Not enough varying numeric columns for correlation analysis")
        df_copy = df_copy[non_const_cols]
        
        corr_matrix = df_copy.corr()
        
        # Ensure diagonal is exactly 1.0 and replace any remaining NaN with 0
        for col in corr_matrix.columns:
            corr_matrix.loc[col, col] = 1.0
        corr_matrix = corr_matrix.fillna(0)
        
        # Convert to list format for frontend
        chart_data = {
            'type': 'heatmap',
            'data': {
                'labels': corr_matrix.columns.tolist(),
                'values': [[float(v) for v in row] for row in corr_matrix.values],
            },
            'options': {
                'title': 'Correlation Matrix',
            }
        }
        
        fig, ax = plt.subplots(figsize=(12, 10))
        sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0, 
                   fmt='.2f', ax=ax, square=True)
        ax.set_title('Correlation Matrix')
        plt.tight_layout()
        
        chart_image = self._generate_matplotlib_image(fig)
        
        # Find strongest correlations
        corr_pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                val = corr_matrix.iloc[i, j]
                corr_val = float(val) if pd.notna(val) else 0.0
                corr_pairs.append({
                    'pair': f"{corr_matrix.columns[i]} - {corr_matrix.columns[j]}",
                    'correlation': corr_val
                })
        
        corr_pairs.sort(key=lambda x: abs(x['correlation']), reverse=True)
        
        # Filter out trivially correlated pairs (|r| >= 0.99)
        meaningful_pairs = [p for p in corr_pairs if abs(p['correlation']) < 0.99]
        top_pair = meaningful_pairs[0] if meaningful_pairs else (corr_pairs[0] if corr_pairs else None)
        
        statistics = {
            'top_correlation': top_pair['pair'] if top_pair else 'N/A',
            'top_correlation_value': round(top_pair['correlation'], 3) if top_pair else 0,
            'columns_analyzed': len(available_cols),
            'rows_analyzed': len(df_copy),
        }
        
        return {
            'chart_data': chart_data,
            'chart_image': chart_image,
            'statistics': statistics
        }
    
    def analyze_mr_complexity(self, df, analysis):
        """
        Analyze MR complexity based on multiple factors
        """
        config = analysis.config
        
        df = self._apply_config(df, config)
        df_copy = df.copy()
        
        # Calculate complexity score
        complexity_factors = []
        
        if '#Commits' in df_copy.columns:
            df_copy['commits_norm'] = pd.to_numeric(df_copy['#Commits'], errors='coerce').fillna(0)
            complexity_factors.append('commits_norm')
        
        if 'modified_files' in df_copy.columns:
            df_copy['files_norm'] = pd.to_numeric(df_copy['modified_files'], errors='coerce').fillna(0)
            complexity_factors.append('files_norm')
        
        # For churn: use initial_mr_size if available, else additions+deletions, else churn columns
        if 'initial_mr_size' in df_copy.columns:
            df_copy['churn_norm'] = pd.to_numeric(df_copy['initial_mr_size'], errors='coerce').fillna(0)
            complexity_factors.append('churn_norm')
        elif 'additions' in df_copy.columns and 'deletions' in df_copy.columns:
            add_col, del_col = 'additions', 'deletions'
            df_copy[add_col] = pd.to_numeric(df_copy[add_col], errors='coerce').fillna(0)
            df_copy[del_col] = pd.to_numeric(df_copy[del_col], errors='coerce').fillna(0)
            df_copy['churn_norm'] = df_copy[add_col] + df_copy[del_col]
            complexity_factors.append('churn_norm')
        elif 'churn_addition' in df_copy.columns and 'churn_deletions' in df_copy.columns:
            add_col, del_col = 'churn_addition', 'churn_deletions'
            df_copy[add_col] = pd.to_numeric(df_copy[add_col], errors='coerce').fillna(0)
            df_copy[del_col] = pd.to_numeric(df_copy[del_col], errors='coerce').fillna(0)
            df_copy['churn_norm'] = df_copy[add_col] + df_copy[del_col]
            complexity_factors.append('churn_norm')
        
        if not complexity_factors:
            raise ValueError("No suitable columns found for complexity analysis")
        
        # Normalize and sum for complexity score
        for col in complexity_factors:
            max_val = df_copy[col].max()
            if max_val > 0:
                df_copy[col] = df_copy[col] / max_val
        
        df_copy['complexity'] = df_copy[complexity_factors].sum(axis=1)
        
        # Categorize complexity
        df_copy['complexity_cat'] = pd.cut(df_copy['complexity'], 
                                           bins=[0, 0.5, 1.0, 1.5, float('inf')],
                                           labels=['Low', 'Medium', 'High', 'Very High'])
        
        complexity_dist = df_copy['complexity_cat'].value_counts()
        
        chart_data = {
            'type': 'pie',
            'data': {
                'labels': complexity_dist.index.tolist(),
                'datasets': [{
                    'data': complexity_dist.values.tolist(),
                }]
            },
            'options': {
                'title': 'MR Complexity Distribution',
            }
        }
        
        fig, ax = plt.subplots(figsize=(10, 8))
        colors = ['#10b981', '#f59e0b', '#ef4444', '#7c3aed']
        ax.pie(complexity_dist.values, labels=complexity_dist.index, autopct='%1.1f%%',
               colors=colors[:len(complexity_dist)], startangle=90)
        ax.set_title('MR Complexity Distribution')
        plt.tight_layout()
        
        chart_image = self._generate_matplotlib_image(fig)
        
        # Flatten complexity breakdown into top-level stats
        flat_stats = {'total_mrs': len(df_copy)}
        for level, count in complexity_dist.items():
            flat_stats[f'{level.lower()}_complexity'] = int(count)
        
        statistics = flat_stats
        
        return {
            'chart_data': chart_data,
            'chart_image': chart_image,
            'statistics': statistics
        }
    
    def analyze_project_comparison(self, df, analysis):
        """
        Compare metrics across different projects
        """
        config = analysis.config
        project_col = config.get('x_axis') or 'Project_ID'
        metric_col = config.get('y_axis') or '#Commits'
        
        df = self._apply_config(df, config)
        
        if project_col not in df.columns:
            raise ValueError(f"Column '{project_col}' not found in dataset")
        
        df_copy = df.copy()
        df_copy[metric_col] = pd.to_numeric(df_copy[metric_col], errors='coerce').fillna(0)
        
        project_stats = df_copy.groupby(project_col)[metric_col].agg(['mean', 'median', 'sum', 'count'])
        project_stats = project_stats.sort_values('count', ascending=False).head(10)
        
        labels = [str(x) for x in project_stats.index]
        
        chart_data = {
            'type': 'bar',
            'data': {
                'labels': labels,
                'datasets': [
                    {
                        'label': 'Mean',
                        'data': project_stats['mean'].values.tolist(),
                    },
                    {
                        'label': 'Median',
                        'data': project_stats['median'].values.tolist(),
                    }
                ]
            },
            'options': {
                'title': f'{metric_col} by Project',
                'xLabel': 'Project',
                'yLabel': metric_col,
            }
        }
        
        fig, ax = plt.subplots(figsize=(12, 6))
        x = range(len(project_stats))
        width = 0.35
        ax.bar([i - width/2 for i in x], project_stats['mean'].values, width, label='Mean', color='steelblue')
        ax.bar([i + width/2 for i in x], project_stats['median'].values, width, label='Median', color='coral')
        ax.set_xlabel('Project')
        ax.set_ylabel(metric_col)
        ax.set_title(f'{metric_col} by Project')
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        chart_image = self._generate_matplotlib_image(fig)
        
        statistics = {
            'projects_count': len(project_stats),
            'total_mrs': int(project_stats['count'].sum()),
        }

        return {
            'chart_data': chart_data,
            'chart_image': chart_image,
            'statistics': statistics
        }

    # ==================== DevOps helpers ====================

    def _devops_hours_between(self, df, start_col, end_col):
        """Return a Series of hours between two datetime columns (NaT → NaN)."""
        start = pd.to_datetime(df[start_col], errors='coerce')
        end = pd.to_datetime(df[end_col], errors='coerce')
        return (end - start).dt.total_seconds() / 3600.0

    def _devops_histogram(self, values, title, x_label, bins=20):
        series = pd.to_numeric(pd.Series(values), errors='coerce').dropna()
        if series.empty:
            return {
                'type': 'histogram',
                'data': {'labels': [], 'datasets': [{'label': x_label, 'data': []}]},
                'title': title,
                'xLabel': x_label,
                'yLabel': 'Count',
            }, {'count': 0}
        counts, edges = np.histogram(series, bins=bins)
        labels = [f"{edges[i]:.1f}–{edges[i+1]:.1f}" for i in range(len(counts))]
        statistics = {
            'count': int(series.count()),
            'mean': float(series.mean()),
            'median': float(series.median()),
            'p90': float(series.quantile(0.9)),
        }
        chart_data = {
            'type': 'histogram',
            'data': {
                'labels': labels,
                'datasets': [{'label': x_label, 'data': [int(c) for c in counts]}],
            },
            'title': title,
            'xLabel': x_label,
            'yLabel': 'Count',
        }
        return chart_data, statistics

    def _devops_time_bucket(self, dt_series, freq):
        """Group a datetime series to a Period with the given freq."""
        dt = pd.to_datetime(dt_series, errors='coerce').dropna()
        return dt.dt.to_period(freq)

    # ==================== Kanban analyses ====================

    def analyze_kanban_lead_time(self, df, analysis):
        df = self._apply_config(df, analysis.config or {})
        hours = self._devops_hours_between(df, 'created_at', 'closed_at').dropna()
        chart_data, statistics = self._devops_histogram(
            hours, 'Lead Time Distribution', 'Hours', bins=20
        )
        chart_data['type'] = analysis.chart_type or 'histogram'
        return {'chart_data': chart_data, 'statistics': statistics}

    def analyze_kanban_cycle_time(self, df, analysis):
        df = self._apply_config(df, analysis.config or {})
        hours = self._devops_hours_between(df, 'in_progress_at', 'done_at').dropna()
        chart_data, statistics = self._devops_histogram(
            hours, 'Cycle Time Distribution', 'Hours', bins=20
        )
        chart_data['type'] = analysis.chart_type or 'box'
        return {'chart_data': chart_data, 'statistics': statistics}

    def analyze_kanban_throughput(self, df, analysis):
        config = analysis.config or {}
        freq = config.get('time_aggregation') or 'W'
        df = self._apply_config(df, config)
        periods = self._devops_time_bucket(df['done_at'], freq)
        counts = periods.groupby(periods).size().sort_index()
        labels = [str(p) for p in counts.index]
        chart_data = {
            'type': analysis.chart_type or 'bar',
            'data': {
                'labels': labels,
                'datasets': [{'label': 'Completed items', 'data': [int(v) for v in counts.values]}],
            },
            'title': f'Throughput (per {freq})',
            'xLabel': 'Period',
            'yLabel': 'Completed items',
        }
        return {'chart_data': chart_data, 'statistics': {'total': int(counts.sum())}}

    def analyze_kanban_wip(self, df, analysis):
        config = analysis.config or {}
        freq = config.get('time_aggregation') or 'D'
        df = self._apply_config(df, config)
        entered = pd.to_datetime(df['entered_at'], errors='coerce')
        left = pd.to_datetime(df['left_at'], errors='coerce')
        mask = entered.notna()
        entered = entered[mask]
        left = left[mask]
        if entered.empty:
            return {
                'chart_data': {
                    'type': analysis.chart_type or 'area',
                    'data': {'labels': [], 'datasets': [{'label': 'WIP', 'data': []}]},
                    'title': 'Work in Progress',
                },
                'statistics': {'max_wip': 0},
            }
        start = entered.min().to_period(freq).to_timestamp()
        end = (left.fillna(pd.Timestamp.utcnow()).max()).to_period(freq).to_timestamp()
        buckets = pd.date_range(start, end, freq=freq)
        wip = []
        for ts in buckets:
            active = ((entered <= ts) & (left.fillna(pd.Timestamp.max) > ts)).sum()
            wip.append(int(active))
        labels = [ts.strftime('%Y-%m-%d') for ts in buckets]
        chart_data = {
            'type': analysis.chart_type or 'area',
            'data': {'labels': labels, 'datasets': [{'label': 'WIP', 'data': wip}]},
            'title': 'Work in Progress Over Time',
            'xLabel': 'Period',
            'yLabel': 'In-flight items',
        }
        return {'chart_data': chart_data, 'statistics': {'max_wip': max(wip) if wip else 0}}

    def analyze_kanban_cfd(self, df, analysis):
        config = analysis.config or {}
        freq = config.get('time_aggregation') or 'D'
        df = self._apply_config(df, config)
        dates = pd.to_datetime(df['date'], errors='coerce').dt.to_period(freq).dt.to_timestamp()
        pivot = (
            df.assign(_period=dates)
              .groupby(['_period', 'column']).size()
              .unstack(fill_value=0)
              .sort_index()
              .cumsum()
        )
        labels = [ts.strftime('%Y-%m-%d') for ts in pivot.index]
        datasets = [
            {'label': col, 'data': [int(v) for v in pivot[col].values]}
            for col in pivot.columns
        ]
        chart_data = {
            'type': analysis.chart_type or 'area',
            'data': {'labels': labels, 'datasets': datasets},
            'title': 'Cumulative Flow Diagram',
            'xLabel': 'Period',
            'yLabel': 'Cumulative items',
            'stacked': True,
        }
        return {'chart_data': chart_data, 'statistics': {'columns': list(pivot.columns)}}

    def analyze_kanban_column_time(self, df, analysis):
        df = self._apply_config(df, analysis.config or {})
        grouped = df.dropna(subset=['column', 'duration_h']).groupby('column')['duration_h']
        labels = list(grouped.groups.keys())
        medians = [float(grouped.get_group(c).median()) for c in labels]
        chart_data = {
            'type': analysis.chart_type or 'bar',
            'data': {
                'labels': labels,
                'datasets': [{'label': 'Median hours', 'data': medians}],
            },
            'title': 'Median Residency per Column',
            'xLabel': 'Column',
            'yLabel': 'Hours',
        }
        return {'chart_data': chart_data, 'statistics': {'columns': labels}}

    def analyze_kanban_blocked_ratio(self, df, analysis):
        df = self._apply_config(df, analysis.config or {})
        labels_col = df['labels'].fillna('').astype(str).str.lower()
        is_blocked = labels_col.str.contains('block')
        blocked_hours = float(df.loc[is_blocked, 'duration_h'].sum() or 0)
        flowing_hours = float(df.loc[~is_blocked, 'duration_h'].sum() or 0)
        chart_data = {
            'type': analysis.chart_type or 'pie',
            'data': {
                'labels': ['Blocked', 'Flowing'],
                'datasets': [{'label': 'Hours', 'data': [blocked_hours, flowing_hours]}],
            },
            'title': 'Blocked vs Flowing Hours',
        }
        total = blocked_hours + flowing_hours
        statistics = {
            'blocked_hours': blocked_hours,
            'flowing_hours': flowing_hours,
            'blocked_ratio': (blocked_hours / total) if total else 0,
        }
        return {'chart_data': chart_data, 'statistics': statistics}

    def analyze_kanban_assignee_load(self, df, analysis):
        df = self._apply_config(df, analysis.config or {})
        open_df = df[df['status'].astype(str).str.lower() != 'closed']
        counts = open_df['assignee'].fillna('Unassigned').value_counts().head(15)
        chart_data = {
            'type': analysis.chart_type or 'bar',
            'data': {
                'labels': counts.index.tolist(),
                'datasets': [{'label': 'Open items', 'data': [int(v) for v in counts.values]}],
            },
            'title': 'Open Items per Assignee',
            'xLabel': 'Assignee',
            'yLabel': 'Open items',
        }
        return {'chart_data': chart_data, 'statistics': {'total_open': int(counts.sum())}}

    # ==================== CI/CD analyses ====================

    def _cicd_normalize_conclusion(self, series):
        """Return a boolean Series: True for success."""
        s = series.fillna('').astype(str).str.lower()
        return s.isin(['success', 'passed', 'ok'])

    def analyze_cicd_success_rate(self, df, analysis):
        config = analysis.config or {}
        freq = config.get('time_aggregation') or 'D'
        df = self._apply_config(df, config)
        periods = self._devops_time_bucket(df['created_at'], freq)
        success = self._cicd_normalize_conclusion(df.loc[periods.index, 'conclusion'])
        grouped = success.groupby(periods)
        rate = (grouped.sum() / grouped.count()).sort_index() * 100.0
        labels = [str(p) for p in rate.index]
        chart_data = {
            'type': analysis.chart_type or 'line',
            'data': {
                'labels': labels,
                'datasets': [{'label': 'Success %', 'data': [float(v) for v in rate.values]}],
            },
            'title': 'CI/CD Success Rate Over Time',
            'xLabel': 'Period',
            'yLabel': 'Success %',
        }
        overall = float(success.mean() * 100) if len(success) else 0.0
        return {'chart_data': chart_data, 'statistics': {'overall_success_pct': overall}}

    def analyze_cicd_build_duration(self, df, analysis):
        config = analysis.config or {}
        freq = config.get('time_aggregation') or 'D'
        df = self._apply_config(df, config)
        duration_min = pd.to_numeric(df['duration_s'], errors='coerce') / 60.0
        periods = self._devops_time_bucket(df['created_at'], freq)
        grouped = duration_min.groupby(periods)
        median = grouped.median().sort_index()
        p90 = grouped.quantile(0.9).sort_index()
        labels = [str(p) for p in median.index]
        chart_data = {
            'type': analysis.chart_type or 'line',
            'data': {
                'labels': labels,
                'datasets': [
                    {'label': 'Median minutes', 'data': [float(v) for v in median.values]},
                    {'label': 'P90 minutes', 'data': [float(v) for v in p90.values]},
                ],
            },
            'title': 'Build Duration Trend',
            'xLabel': 'Period',
            'yLabel': 'Minutes',
        }
        statistics = {
            'median_minutes': float(duration_min.median()) if not duration_min.empty else 0.0,
            'p90_minutes': float(duration_min.quantile(0.9)) if not duration_min.empty else 0.0,
        }
        return {'chart_data': chart_data, 'statistics': statistics}

    def analyze_cicd_failure_rate_by_job(self, df, analysis):
        df = self._apply_config(df, analysis.config or {})
        success = self._cicd_normalize_conclusion(df['conclusion'])
        grouped = success.groupby(df['job_name'])
        fail_rate = (1 - grouped.mean()) * 100.0
        fail_rate = fail_rate.sort_values(ascending=False).head(20)
        chart_data = {
            'type': analysis.chart_type or 'bar',
            'data': {
                'labels': fail_rate.index.tolist(),
                'datasets': [{'label': 'Failure %', 'data': [float(v) for v in fail_rate.values]}],
            },
            'title': 'Failure Rate by Job',
            'xLabel': 'Job',
            'yLabel': 'Failure %',
        }
        return {'chart_data': chart_data, 'statistics': {'worst_job': fail_rate.index[0] if len(fail_rate) else None}}

    def analyze_cicd_mttr(self, df, analysis):
        config = analysis.config or {}
        freq = config.get('time_aggregation') or 'W'
        df = self._apply_config(df, config).sort_values('created_at')
        success = self._cicd_normalize_conclusion(df['conclusion'])
        created = pd.to_datetime(df['created_at'], errors='coerce')
        recovery_min = []
        recovery_periods = []
        open_failure_at = None
        for ts, ok in zip(created, success):
            if pd.isna(ts):
                continue
            if not ok and open_failure_at is None:
                open_failure_at = ts
            elif ok and open_failure_at is not None:
                recovery_min.append((ts - open_failure_at).total_seconds() / 60.0)
                recovery_periods.append(ts.to_period(freq))
                open_failure_at = None
        if not recovery_min:
            chart_data = {
                'type': analysis.chart_type or 'line',
                'data': {'labels': [], 'datasets': [{'label': 'MTTR minutes', 'data': []}]},
                'title': 'Mean Time To Recovery',
            }
            return {'chart_data': chart_data, 'statistics': {'mttr_minutes': 0}}
        series = pd.Series(recovery_min, index=recovery_periods)
        mttr = series.groupby(series.index).mean().sort_index()
        labels = [str(p) for p in mttr.index]
        chart_data = {
            'type': analysis.chart_type or 'line',
            'data': {
                'labels': labels,
                'datasets': [{'label': 'MTTR minutes', 'data': [float(v) for v in mttr.values]}],
            },
            'title': 'Mean Time To Recovery',
            'xLabel': 'Period',
            'yLabel': 'Minutes',
        }
        return {'chart_data': chart_data, 'statistics': {'mttr_minutes': float(series.mean())}}

    def analyze_cicd_deploy_frequency(self, df, analysis):
        config = analysis.config or {}
        freq = config.get('time_aggregation') or 'W'
        df = self._apply_config(df, config)
        deploy_mask = df['workflow_name'].fillna('').astype(str).str.contains('deploy', case=False)
        success = self._cicd_normalize_conclusion(df['conclusion'])
        deploys = df[deploy_mask & success]
        periods = self._devops_time_bucket(deploys['created_at'], freq)
        counts = periods.groupby(periods).size().sort_index()
        labels = [str(p) for p in counts.index]
        chart_data = {
            'type': analysis.chart_type or 'bar',
            'data': {
                'labels': labels,
                'datasets': [{'label': 'Deployments', 'data': [int(v) for v in counts.values]}],
            },
            'title': f'Deployment Frequency (per {freq})',
            'xLabel': 'Period',
            'yLabel': 'Deployments',
        }
        return {'chart_data': chart_data, 'statistics': {'total_deploys': int(counts.sum())}}

    def analyze_cicd_queue_time(self, df, analysis):
        df = self._apply_config(df, analysis.config or {})
        queue_s = (
            pd.to_datetime(df['started_at'], errors='coerce')
            - pd.to_datetime(df['created_at'], errors='coerce')
        ).dt.total_seconds()
        queue_s = queue_s.dropna()
        queue_s = queue_s[queue_s >= 0]
        chart_data, statistics = self._devops_histogram(
            queue_s, 'Queue Time Distribution', 'Seconds', bins=20
        )
        chart_data['type'] = analysis.chart_type or 'histogram'
        return {'chart_data': chart_data, 'statistics': statistics}

    def analyze_cicd_runner_utilization(self, df, analysis):
        df = self._apply_config(df, analysis.config or {})
        started = pd.to_datetime(df['started_at'], errors='coerce')
        duration_min = pd.to_numeric(df['duration_s'], errors='coerce') / 60.0
        hours = started.dt.hour
        pivot = (
            pd.DataFrame({
                'runner': df['runner_name'].fillna('unknown'),
                'hour': hours,
                'minutes': duration_min,
            })
            .dropna()
            .groupby(['runner', 'hour'])['minutes'].sum()
            .unstack(fill_value=0)
        )
        heatmap = []
        runners = pivot.index.tolist()
        hour_labels = [int(h) for h in pivot.columns.tolist()]
        for i, runner in enumerate(runners):
            for j, hour in enumerate(hour_labels):
                heatmap.append([j, i, float(pivot.iloc[i, j])])
        chart_data = {
            'type': 'heatmap',
            'data': {
                'xLabels': [f'{h:02d}:00' for h in hour_labels],
                'yLabels': runners,
                'values': heatmap,
            },
            'title': 'Runner Utilization (minutes per hour)',
            'xLabel': 'Hour of day',
            'yLabel': 'Runner',
        }
        return {'chart_data': chart_data, 'statistics': {'runners': runners}}

    def analyze_cicd_flaky_jobs(self, df, analysis):
        df = self._apply_config(df, analysis.config or {})
        success = self._cicd_normalize_conclusion(df['conclusion'])
        grouped = (
            df.assign(_ok=success)
              .groupby(['sha', 'job_name'])['_ok']
              .agg(['nunique', 'count'])
              .reset_index()
        )
        # A flaky job/sha has both a success and a failure.
        flaky = grouped[grouped['nunique'] > 1]
        counts = flaky.groupby('job_name').size().sort_values(ascending=False).head(20)
        chart_data = {
            'type': analysis.chart_type or 'bar',
            'data': {
                'labels': counts.index.tolist(),
                'datasets': [{'label': 'Flaky occurrences', 'data': [int(v) for v in counts.values]}],
            },
            'title': 'Flaky Jobs (conclusion flipped on same SHA)',
            'xLabel': 'Job',
            'yLabel': 'Flaky SHAs',
        }
        return {'chart_data': chart_data, 'statistics': {'flaky_jobs': int(len(counts))}}
