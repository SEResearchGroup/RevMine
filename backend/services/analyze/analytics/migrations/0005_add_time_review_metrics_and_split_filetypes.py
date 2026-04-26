"""
Django data migration to:
1. Add five code-review time metrics:
   pickup_time, time_to_first_review, review_duration, approval_time, cycle_time
2. Add split filetype metrics:
   filetypes_by_extension, filetypes_by_count
3. Deactivate the old combined filetypes_distribution metric
"""

from django.db import migrations


def add_new_metrics(apps, schema_editor):
    MetricDefinition = apps.get_model('analytics', 'MetricDefinition')

    # ── Deactivate old combined filetypes chart ───────────────────────
    MetricDefinition.objects.filter(code='filetypes_distribution').update(is_active=False)

    # ── New metrics ───────────────────────────────────────────────────
    new_metrics = [
        # ---- File type split ----------------------------------------
        {
            'code': 'filetypes_by_extension',
            'name': 'File Types by Extension',
            'description': 'Number of MRs that touched each file extension (top 25)',
            'category': 'code_quality',
            'default_chart_type': 'bar',
            'supported_chart_types': ['bar', 'pie'],
            'required_columns': ['filetypes'],
            'supports_time_aggregation': False,
            'supports_custom_axes': False,
            'analysis_function': 'filetypes_by_extension',
        },
        {
            'code': 'filetypes_by_count',
            'name': 'File Types by Count',
            'description': 'Distribution of MRs by the number of unique file types changed',
            'category': 'code_quality',
            'default_chart_type': 'bar',
            'supported_chart_types': ['bar'],
            'required_columns': ['filetypes'],
            'supports_time_aggregation': False,
            'supports_custom_axes': False,
            'analysis_function': 'filetypes_by_count',
        },
        # ---- Code-review time metrics --------------------------------
        {
            'code': 'pickup_time',
            'name': 'Pickup Time',
            'description': 'Time (hours) from PR creation to the first formal review action',
            'category': 'timeseries',
            'default_chart_type': 'bar',
            'supported_chart_types': ['bar'],
            'required_columns': ['pickup_time'],
            'supports_time_aggregation': False,
            'supports_custom_axes': False,
            'analysis_function': 'pickup_time',
        },
        {
            'code': 'time_to_first_review',
            'name': 'Time to First Review (TTFR)',
            'description': 'Time (hours) from PR creation to the first comment or feedback',
            'category': 'timeseries',
            'default_chart_type': 'bar',
            'supported_chart_types': ['bar'],
            'required_columns': ['time_to_first_review'],
            'supports_time_aggregation': False,
            'supports_custom_axes': False,
            'analysis_function': 'time_to_first_review',
        },
        {
            'code': 'review_duration',
            'name': 'Review Duration',
            'description': 'Time (hours) from the first feedback to merge',
            'category': 'timeseries',
            'default_chart_type': 'bar',
            'supported_chart_types': ['bar'],
            'required_columns': ['review_duration'],
            'supports_time_aggregation': False,
            'supports_custom_axes': False,
            'analysis_function': 'review_duration',
        },
        {
            'code': 'approval_time',
            'name': 'Approval Time',
            'description': 'Time (hours) from the first review to the final approval',
            'category': 'timeseries',
            'default_chart_type': 'bar',
            'supported_chart_types': ['bar'],
            'required_columns': ['approval_time'],
            'supports_time_aggregation': False,
            'supports_custom_axes': False,
            'analysis_function': 'approval_time',
        },
        {
            'code': 'cycle_time',
            'name': 'Cycle Time',
            'description': 'Total time (hours) from PR creation to merge',
            'category': 'timeseries',
            'default_chart_type': 'bar',
            'supported_chart_types': ['bar'],
            'required_columns': ['cycle_time'],
            'supports_time_aggregation': False,
            'supports_custom_axes': False,
            'analysis_function': 'cycle_time',
        },
    ]

    for metric_data in new_metrics:
        if not MetricDefinition.objects.filter(code=metric_data['code']).exists():
            MetricDefinition.objects.create(**metric_data)


def reverse_migration(apps, schema_editor):
    MetricDefinition = apps.get_model('analytics', 'MetricDefinition')

    # Remove new metrics
    MetricDefinition.objects.filter(
        code__in=[
            'filetypes_by_extension', 'filetypes_by_count',
            'pickup_time', 'time_to_first_review', 'review_duration',
            'approval_time', 'cycle_time',
        ]
    ).delete()

    # Re-activate old combined chart
    MetricDefinition.objects.filter(code='filetypes_distribution').update(is_active=True)


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0004_add_top_charts_remove_custom'),
    ]

    operations = [
        migrations.RunPython(add_new_metrics, reverse_migration),
    ]
