"""
Django data migration to:
1. Remove the custom_chart metric definition
2. Add three new metrics: top_commiters, top_authors, top_reviewers
"""

from django.db import migrations


def add_new_metrics_and_remove_custom(apps, schema_editor):
    MetricDefinition = apps.get_model('analytics', 'MetricDefinition')

    # ── Remove custom_chart ──────────────────────────────────────────
    MetricDefinition.objects.filter(code='custom_chart').delete()

    # ── Add new metrics ──────────────────────────────────────────────
    new_metrics = [
        {
            'code': 'top_commiters',
            'name': 'Top 10 Committers',
            'description': 'Top 10 committers ranked by number of MRs they contributed to',
            'category': 'collaboration',
            'default_chart_type': 'bar',
            'supported_chart_types': ['bar', 'pie'],
            'required_columns': ['Commiters'],
            'supports_time_aggregation': False,
            'supports_custom_axes': False,
            'analysis_function': 'top_commiters',
        },
        {
            'code': 'top_authors',
            'name': 'Top 10 Authors',
            'description': 'Top 10 authors ranked by number of MRs they authored',
            'category': 'collaboration',
            'default_chart_type': 'bar',
            'supported_chart_types': ['bar', 'pie'],
            'required_columns': ['Author'],
            'supports_time_aggregation': False,
            'supports_custom_axes': False,
            'analysis_function': 'top_authors',
        },
        {
            'code': 'top_reviewers',
            'name': 'Top 10 Reviewers',
            'description': 'Top 10 reviewers ranked by number of MRs they reviewed',
            'category': 'collaboration',
            'default_chart_type': 'bar',
            'supported_chart_types': ['bar', 'pie'],
            'required_columns': ['Reviewers'],
            'supports_time_aggregation': False,
            'supports_custom_axes': False,
            'analysis_function': 'top_reviewers',
        },
    ]

    for metric_data in new_metrics:
        if not MetricDefinition.objects.filter(code=metric_data['code']).exists():
            MetricDefinition.objects.create(**metric_data)


def reverse_migration(apps, schema_editor):
    MetricDefinition = apps.get_model('analytics', 'MetricDefinition')

    # Remove new metrics
    MetricDefinition.objects.filter(
        code__in=['top_commiters', 'top_authors', 'top_reviewers']
    ).delete()

    # Restore custom_chart
    if not MetricDefinition.objects.filter(code='custom_chart').exists():
        MetricDefinition.objects.create(
            code='custom_chart',
            name='Custom Chart',
            description='Create a custom chart with any X/Y axes',
            category='custom',
            default_chart_type='bar',
            supported_chart_types=['bar', 'line', 'scatter', 'pie', 'area'],
            required_columns=[],
            supports_time_aggregation=True,
            supports_custom_axes=True,
            default_aggregation='sum',
            analysis_function='custom_chart',
        )


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0003_add_missing_metrics_and_fix_required_columns'),
    ]

    operations = [
        migrations.RunPython(add_new_metrics_and_remove_custom, reverse_migration),
    ]
