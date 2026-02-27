"""
Django data migration to:
1. Add missing metric definitions (9 analysis functions had no MetricDefinition)
2. Fix required_columns for code_churn and mr_size_analysis to accept
   alternative column names present in different dataset formats.
"""

from django.db import migrations


def add_missing_metrics_and_fix(apps, schema_editor):
    MetricDefinition = apps.get_model('analytics', 'MetricDefinition')

    # ── Fix existing metrics ──────────────────────────────────────────────
    # code_churn: accept either (additions, deletions) or (churn_addition, churn_deletions)
    MetricDefinition.objects.filter(code='code_churn').update(
        required_columns=['Creation_Date'],  # columns checked dynamically in function
        description='Analysis of code additions and deletions over time. Works with additions/deletions or churn_addition/churn_deletions columns.',
    )

    # churn_scatter: same flexibility
    MetricDefinition.objects.filter(code='churn_scatter').update(
        required_columns=[],  # columns checked dynamically in function
        description='Scatter plot of additions vs deletions per MR. Works with additions/deletions or churn_addition/churn_deletions columns.',
    )

    # mr_size_analysis: use initial_mr_size directly
    MetricDefinition.objects.filter(code='mr_size_analysis').update(
        required_columns=[],  # columns checked dynamically in function
        description='Distribution of merge request size. Uses initial_mr_size or additions+deletions.',
    )

    # ── Add missing metrics ──────────────────────────────────────────────
    new_metrics = [
        {
            'code': 'commit_time_analysis',
            'name': 'MR Creation Time of Day',
            'description': 'Distribution of MR creation by hour of day',
            'category': 'timeseries',
            'default_chart_type': 'bar',
            'supported_chart_types': ['bar', 'line'],
            'required_columns': ['Creation_Date'],
            'supports_time_aggregation': False,
            'supports_custom_axes': False,
            'analysis_function': 'commit_time_analysis',
        },
        {
            'code': 'collaboration_metrics',
            'name': 'Collaboration Metrics',
            'description': 'Average collaboration metrics per MR: people, reviewers, commiters, discussionners',
            'category': 'collaboration',
            'default_chart_type': 'bar',
            'supported_chart_types': ['bar', 'pie'],
            'required_columns': ['#people', '#reviewers'],
            'supports_time_aggregation': False,
            'supports_custom_axes': False,
            'analysis_function': 'collaboration_metrics',
        },
        {
            'code': 'comments_analysis',
            'name': 'Comments Analysis',
            'description': 'Distribution of comments per merge request',
            'category': 'collaboration',
            'default_chart_type': 'bar',
            'supported_chart_types': ['bar', 'histogram'],
            'required_columns': ['comments'],
            'supports_time_aggregation': False,
            'supports_custom_axes': False,
            'analysis_function': 'comments_analysis',
        },
        {
            'code': 'filetypes_distribution',
            'name': 'File Types Distribution',
            'description': 'Distribution of number of file types per MR',
            'category': 'code_quality',
            'default_chart_type': 'bar',
            'supported_chart_types': ['bar', 'pie'],
            'required_columns': ['filetypes'],
            'supports_time_aggregation': False,
            'supports_custom_axes': False,
            'analysis_function': 'filetypes_distribution',
        },
        {
            'code': 'entropy_analysis',
            'name': 'Historical Entropy',
            'description': 'Distribution of historical entropy across merge requests',
            'category': 'code_quality',
            'default_chart_type': 'histogram',
            'supported_chart_types': ['histogram', 'bar', 'box'],
            'required_columns': ['hist_entropy'],
            'supports_time_aggregation': False,
            'supports_custom_axes': False,
            'analysis_function': 'entropy_analysis',
        },
        {
            'code': 'rework_analysis',
            'name': 'Rework Analysis',
            'description': 'Distribution of rework size in merge requests',
            'category': 'code_quality',
            'default_chart_type': 'histogram',
            'supported_chart_types': ['histogram', 'bar'],
            'required_columns': ['rework_size'],
            'supports_time_aggregation': False,
            'supports_custom_axes': False,
            'analysis_function': 'rework_analysis',
        },
        {
            'code': 'correlation_matrix',
            'name': 'Correlation Matrix',
            'description': 'Correlation heatmap between numeric columns in the dataset',
            'category': 'correlation',
            'default_chart_type': 'heatmap',
            'supported_chart_types': ['heatmap'],
            'required_columns': [],  # auto-detects numeric columns
            'supports_time_aggregation': False,
            'supports_custom_axes': False,
            'analysis_function': 'correlation_matrix',
        },
        {
            'code': 'mr_complexity',
            'name': 'MR Complexity',
            'description': 'MR complexity score based on commits, files modified, and code churn',
            'category': 'overview',
            'default_chart_type': 'pie',
            'supported_chart_types': ['pie', 'bar'],
            'required_columns': ['#Commits'],
            'supports_time_aggregation': False,
            'supports_custom_axes': False,
            'analysis_function': 'mr_complexity',
        },
        {
            'code': 'project_comparison',
            'name': 'Project Comparison',
            'description': 'Compare metrics across different projects',
            'category': 'overview',
            'default_chart_type': 'bar',
            'supported_chart_types': ['bar', 'line'],
            'required_columns': ['Project_ID'],
            'supports_time_aggregation': False,
            'supports_custom_axes': True,
            'default_aggregation': 'mean',
            'analysis_function': 'project_comparison',
        },
    ]

    for metric_data in new_metrics:
        if not MetricDefinition.objects.filter(code=metric_data['code']).exists():
            MetricDefinition.objects.create(**metric_data)


def reverse_migration(apps, schema_editor):
    MetricDefinition = apps.get_model('analytics', 'MetricDefinition')
    new_codes = [
        'commit_time_analysis', 'collaboration_metrics', 'comments_analysis',
        'filetypes_distribution', 'entropy_analysis', 'rework_analysis',
        'correlation_matrix', 'mr_complexity', 'project_comparison',
    ]
    MetricDefinition.objects.filter(code__in=new_codes).delete()

    # Restore original required_columns
    MetricDefinition.objects.filter(code='code_churn').update(
        required_columns=['churn_addition', 'churn_deletions'],
    )
    MetricDefinition.objects.filter(code='churn_scatter').update(
        required_columns=['churn_addition', 'churn_deletions'],
    )
    MetricDefinition.objects.filter(code='mr_size_analysis').update(
        required_columns=['initial_mr_size'],
    )


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0002_initial_metrics'),
    ]

    operations = [
        migrations.RunPython(add_missing_metrics_and_fix, reverse_migration),
    ]
