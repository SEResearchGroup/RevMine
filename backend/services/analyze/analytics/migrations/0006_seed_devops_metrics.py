"""
Seed MetricDefinition entries for Kanban and CI/CD DevOps analyses.
Each metric references an analysis_function implemented in analysis_functions.py.
"""

from django.db import migrations


KANBAN_METRICS = [
    {
        "code": "kanban_lead_time",
        "name": "Lead Time Distribution",
        "description": "Distribution of lead time (created → closed) per issue.",
        "category": "distribution",
        "default_chart_type": "histogram",
        "supported_chart_types": ["histogram", "box", "bar"],
        "required_columns": ["created_at", "closed_at"],
        "supports_time_aggregation": False,
        "supports_custom_axes": False,
        "analysis_function": "kanban_lead_time",
    },
    {
        "code": "kanban_cycle_time",
        "name": "Cycle Time Distribution",
        "description": "Time spent actively in progress (in_progress → done) per issue.",
        "category": "distribution",
        "default_chart_type": "box",
        "supported_chart_types": ["box", "histogram", "bar"],
        "required_columns": ["in_progress_at", "done_at"],
        "supports_time_aggregation": False,
        "supports_custom_axes": False,
        "analysis_function": "kanban_cycle_time",
    },
    {
        "code": "kanban_throughput",
        "name": "Throughput",
        "description": "Number of issues completed per time period.",
        "category": "timeseries",
        "default_chart_type": "bar",
        "supported_chart_types": ["bar", "line", "area"],
        "required_columns": ["done_at"],
        "supports_time_aggregation": True,
        "supports_custom_axes": False,
        "default_aggregation": "count",
        "analysis_function": "kanban_throughput",
    },
    {
        "code": "kanban_wip",
        "name": "Work in Progress Over Time",
        "description": "Count of issues in WIP columns over time.",
        "category": "timeseries",
        "default_chart_type": "area",
        "supported_chart_types": ["area", "line", "bar"],
        "required_columns": ["column", "entered_at", "left_at"],
        "supports_time_aggregation": True,
        "supports_custom_axes": False,
        "analysis_function": "kanban_wip",
    },
    {
        "code": "kanban_cfd",
        "name": "Cumulative Flow Diagram",
        "description": "Stacked area of issue counts per column over time.",
        "category": "timeseries",
        "default_chart_type": "area",
        "supported_chart_types": ["area", "line"],
        "required_columns": ["column", "date"],
        "supports_time_aggregation": True,
        "supports_custom_axes": False,
        "analysis_function": "kanban_cfd",
    },
    {
        "code": "kanban_column_time",
        "name": "Column Residency Time",
        "description": "Distribution of time items spend in each column.",
        "category": "distribution",
        "default_chart_type": "box",
        "supported_chart_types": ["box", "bar"],
        "required_columns": ["column", "duration_h"],
        "supports_time_aggregation": False,
        "supports_custom_axes": False,
        "analysis_function": "kanban_column_time",
    },
    {
        "code": "kanban_blocked_ratio",
        "name": "Blocked vs. Unblocked Ratio",
        "description": "Share of time items spent blocked versus flowing.",
        "category": "composition",
        "default_chart_type": "pie",
        "supported_chart_types": ["pie", "bar"],
        "required_columns": ["labels", "duration_h"],
        "supports_time_aggregation": False,
        "supports_custom_axes": False,
        "analysis_function": "kanban_blocked_ratio",
    },
    {
        "code": "kanban_assignee_load",
        "name": "Assignee Load",
        "description": "Open items per assignee.",
        "category": "collaboration",
        "default_chart_type": "bar",
        "supported_chart_types": ["bar", "pie"],
        "required_columns": ["assignee", "status"],
        "supports_time_aggregation": False,
        "supports_custom_axes": False,
        "analysis_function": "kanban_assignee_load",
    },
]


CICD_METRICS = [
    {
        "code": "cicd_success_rate",
        "name": "Success Rate Over Time",
        "description": "Share of pipeline runs that succeeded, aggregated per period.",
        "category": "timeseries",
        "default_chart_type": "line",
        "supported_chart_types": ["line", "bar", "area"],
        "required_columns": ["conclusion", "created_at"],
        "supports_time_aggregation": True,
        "supports_custom_axes": False,
        "analysis_function": "cicd_success_rate",
    },
    {
        "code": "cicd_build_duration",
        "name": "Build Duration Trend",
        "description": "Median/percentile pipeline duration over time.",
        "category": "timeseries",
        "default_chart_type": "line",
        "supported_chart_types": ["line", "bar", "area"],
        "required_columns": ["duration_s", "created_at"],
        "supports_time_aggregation": True,
        "supports_custom_axes": False,
        "analysis_function": "cicd_build_duration",
    },
    {
        "code": "cicd_failure_rate_by_job",
        "name": "Failure Rate by Job",
        "description": "Failure ratio per job/workflow name.",
        "category": "distribution",
        "default_chart_type": "bar",
        "supported_chart_types": ["bar", "pie"],
        "required_columns": ["job_name", "conclusion"],
        "supports_time_aggregation": False,
        "supports_custom_axes": False,
        "analysis_function": "cicd_failure_rate_by_job",
    },
    {
        "code": "cicd_mttr",
        "name": "Mean Time To Recovery",
        "description": "Mean minutes between a failed run and the next successful run.",
        "category": "timeseries",
        "default_chart_type": "line",
        "supported_chart_types": ["line", "bar"],
        "required_columns": ["conclusion", "created_at"],
        "supports_time_aggregation": True,
        "supports_custom_axes": False,
        "analysis_function": "cicd_mttr",
    },
    {
        "code": "cicd_deploy_frequency",
        "name": "Deployment Frequency",
        "description": "Successful deployment runs per period.",
        "category": "timeseries",
        "default_chart_type": "bar",
        "supported_chart_types": ["bar", "line"],
        "required_columns": ["workflow_name", "conclusion", "created_at"],
        "supports_time_aggregation": True,
        "supports_custom_axes": False,
        "analysis_function": "cicd_deploy_frequency",
    },
    {
        "code": "cicd_queue_time",
        "name": "Queue Time Distribution",
        "description": "Wait between job creation and actual start.",
        "category": "distribution",
        "default_chart_type": "histogram",
        "supported_chart_types": ["histogram", "box", "bar"],
        "required_columns": ["created_at", "started_at"],
        "supports_time_aggregation": False,
        "supports_custom_axes": False,
        "analysis_function": "cicd_queue_time",
    },
    {
        "code": "cicd_runner_utilization",
        "name": "Runner Utilization",
        "description": "Active runner-minutes bucketed by runner × hour.",
        "category": "correlation",
        "default_chart_type": "heatmap",
        "supported_chart_types": ["heatmap", "bar"],
        "required_columns": ["runner_name", "duration_s", "started_at"],
        "supports_time_aggregation": False,
        "supports_custom_axes": False,
        "analysis_function": "cicd_runner_utilization",
    },
    {
        "code": "cicd_flaky_jobs",
        "name": "Flaky Jobs",
        "description": "Jobs that flip conclusion on the same commit SHA.",
        "category": "distribution",
        "default_chart_type": "bar",
        "supported_chart_types": ["bar"],
        "required_columns": ["job_name", "conclusion", "sha"],
        "supports_time_aggregation": False,
        "supports_custom_axes": False,
        "analysis_function": "cicd_flaky_jobs",
    },
]


def seed(apps, schema_editor):
    MetricDefinition = apps.get_model("analytics", "MetricDefinition")
    for meta in KANBAN_METRICS:
        MetricDefinition.objects.update_or_create(
            code=meta["code"],
            defaults={**meta, "source_type": "kanban"},
        )
    for meta in CICD_METRICS:
        MetricDefinition.objects.update_or_create(
            code=meta["code"],
            defaults={**meta, "source_type": "cicd"},
        )


def unseed(apps, schema_editor):
    MetricDefinition = apps.get_model("analytics", "MetricDefinition")
    codes = [m["code"] for m in KANBAN_METRICS + CICD_METRICS]
    MetricDefinition.objects.filter(code__in=codes).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0005_add_devops_source_type"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
