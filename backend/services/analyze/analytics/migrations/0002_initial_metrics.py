"""
Django data migration to create initial metric definitions
Run with: python manage.py migrate
"""

from django.db import migrations


def create_initial_metrics(apps, schema_editor):
    """Create initial metric definitions"""
    MetricDefinition = apps.get_model('analytics', 'MetricDefinition')
    
    metrics = [
        {
            'code': 'commits_over_time',
            'name': 'Commits Over Time',
            'description': 'Visualize the number of commits over time with customizable time aggregation',
            'category': 'timeseries',
            'default_chart_type': 'line',
            'supported_chart_types': ['line', 'bar', 'area'],
            'required_columns': ['Creation_Date', '#Commits'],
            'supports_time_aggregation': True,
            'supports_custom_axes': True,
            'default_aggregation': 'sum',
            'analysis_function': 'commits_over_time',
        },
        {
            'code': 'mr_creation_timeline',
            'name': 'MR Creation Timeline',
            'description': 'Timeline of merge request creation',
            'category': 'timeseries',
            'default_chart_type': 'bar',
            'supported_chart_types': ['bar', 'line', 'area'],
            'required_columns': ['Creation_Date'],
            'supports_time_aggregation': True,
            'supports_custom_axes': False,
            'analysis_function': 'mr_creation_timeline',
        },
        {
            'code': 'lead_time_distribution',
            'name': 'Lead Time Distribution',
            'description': 'Distribution of lead time for merge requests',
            'category': 'distribution',
            'default_chart_type': 'histogram',
            'supported_chart_types': ['histogram', 'box'],
            'required_columns': ['Lead_Time'],
            'supports_time_aggregation': False,
            'supports_custom_axes': True,
            'analysis_function': 'lead_time_distribution',
        },
        {
            'code': 'commits_distribution',
            'name': 'Commits Distribution',
            'description': 'Distribution of the number of commits per MR',
            'category': 'distribution',
            'default_chart_type': 'bar',
            'supported_chart_types': ['bar', 'histogram'],
            'required_columns': ['#Commits'],
            'supports_time_aggregation': False,
            'supports_custom_axes': True,
            'analysis_function': 'commits_distribution',
        },
        {
            'code': 'commiters_analysis',
            'name': 'Contributors Analysis',
            'description': 'Analysis of unique contributors per MR',
            'category': 'collaboration',
            'default_chart_type': 'bar',
            'supported_chart_types': ['bar', 'pie'],
            'required_columns': ['#UniqueCommiters'],
            'supports_time_aggregation': False,
            'supports_custom_axes': True,
            'analysis_function': 'commiters_analysis',
        },
        {
            'code': 'code_churn',
            'name': 'Code Churn Analysis',
            'description': 'Analysis of code additions and deletions',
            'category': 'code_quality',
            'default_chart_type': 'bar',
            'supported_chart_types': ['bar', 'histogram'],
            'required_columns': ['churn_addition', 'churn_deletions'],
            'supports_time_aggregation': False,
            'supports_custom_axes': True,
            'analysis_function': 'code_churn',
        },
        {
            'code': 'churn_scatter',
            'name': 'Churn Correlation',
            'description': 'Scatter plot of additions vs deletions',
            'category': 'correlation',
            'default_chart_type': 'scatter',
            'supported_chart_types': ['scatter'],
            'required_columns': ['churn_addition', 'churn_deletions'],
            'supports_time_aggregation': False,
            'supports_custom_axes': True,
            'analysis_function': 'churn_scatter',
        },
        {
            'code': 'mr_size_analysis',
            'name': 'MR Size Analysis',
            'description': 'Distribution of initial merge request size',
            'category': 'distribution',
            'default_chart_type': 'histogram',
            'supported_chart_types': ['histogram', 'box', 'bar'],
            'required_columns': ['initial_mr_size'],
            'supports_time_aggregation': False,
            'supports_custom_axes': True,
            'analysis_function': 'mr_size_analysis',
        },
        {
            'code': 'discussions_analysis',
            'name': 'Discussions Analysis',
            'description': 'Analysis of the number of discussions per MR',
            'category': 'collaboration',
            'default_chart_type': 'bar',
            'supported_chart_types': ['bar', 'histogram'],
            'required_columns': ['#Discussions'],
            'supports_time_aggregation': False,
            'supports_custom_axes': True,
            'analysis_function': 'discussions_analysis',
        },
        {
            'code': 'files_modified',
            'name': 'Files Modified Analysis',
            'description': 'Distribution of the number of modified files per MR',
            'category': 'code_quality',
            'default_chart_type': 'bar',
            'supported_chart_types': ['bar', 'histogram'],
            'required_columns': ['modified_files'],
            'supports_time_aggregation': False,
            'supports_custom_axes': True,
            'analysis_function': 'files_modified',
        },
        {
            'code': 'state_distribution',
            'name': 'MR State Distribution',
            'description': 'Distribution of merge request states',
            'category': 'overview',
            'default_chart_type': 'pie',
            'supported_chart_types': ['pie', 'bar'],
            'required_columns': ['state'],
            'supports_time_aggregation': False,
            'supports_custom_axes': True,
            'analysis_function': 'state_distribution',
        },
        {
            'code': 'custom_chart',
            'name': 'Custom Chart',
            'description': 'Create custom charts with user-defined X and Y axes',
            'category': 'custom',
            'default_chart_type': 'bar',
            'supported_chart_types': ['bar', 'line', 'scatter', 'area'],
            'required_columns': [],  # No specific requirements
            'supports_time_aggregation': True,
            'supports_custom_axes': True,
            'default_aggregation': 'sum',
            'analysis_function': 'custom_chart',
        },
    ]
    
    for metric_data in metrics:
        MetricDefinition.objects.create(**metric_data)


def reverse_migration(apps, schema_editor):
    """Delete all metric definitions"""
    MetricDefinition = apps.get_model('your_app_name', 'MetricDefinition')
    MetricDefinition.objects.all().delete()


class Migration(migrations.Migration):
    
    dependencies = [
        ('analytics', '0001_initial'),
    ]
    
    operations = [
        migrations.RunPython(create_initial_metrics, reverse_migration),
    ]