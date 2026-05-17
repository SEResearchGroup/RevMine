#!/usr/bin/env python3
"""
Analytics API Test Script
=========================
Run this script to test all analytics API endpoints.

Usage:
    python test_api.py [--base-url https://api.example.test/api/analysis]

Requirements:
    pip install requests
"""

import requests
import json
import sys
import os
from pathlib import Path

# Configuration
BASE_URL = os.environ.get("API_BASE_URL", "https://api.example.test/api/analysis")
SAMPLE_DATA_PATH = Path(__file__).parent / "sample_data.csv"


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def log_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")


def log_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")


def log_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.RESET}")


def log_header(msg):
    print(f"\n{Colors.BOLD}{Colors.YELLOW}{'='*60}")
    print(f" {msg}")
    print(f"{'='*60}{Colors.RESET}\n")


def call_endpoint(method, url, data=None, files=None, expected_status=200, description="", token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzcyMTQ3NjExLCJpYXQiOjE3NzIxNDQwMTEsImp0aSI6IjRlMzBhNGU4MDVmZDRlZTI4NDVhNDQ3M2FiZjc4YWQ0IiwidXNlcl9pZCI6IjEifQ.4Bg-AUGnm6iVQVRLhjiIR1MwHR2xTUGvGfN2w07F8kw):"):
    """Test a single endpoint and return the response"""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            if files:
                response = requests.post(url, data=data, files=files, headers={"Authorization": f"Bearer {token}"} if token else {})
            else:
                response = requests.post(url, json=data, headers=headers)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unknown method: {method}")

        if response.status_code == expected_status:
            log_success(f"{description} - Status: {response.status_code}")
            return response.json() if response.content else None
        else:
            log_error(f"{description} - Expected {expected_status}, got {response.status_code}")
            try:
                print(f"   Response: {response.json()}")
            except ValueError:
                print(f"   Response: {response.text[:200]}")
            return None

    except requests.exceptions.ConnectionError:
        log_error(f"{description} - Connection refused. Is the server running?")
        return None
    except Exception as e:
        log_error(f"{description} - Exception: {e}")
        return None


def run_tests():
    """Run all API tests"""
    dataset_id = None
    analysis_id = None

    # =========================================================================
    log_header("METRICS ENDPOINTS (Read-only)")
    # =========================================================================

    # List all metrics
    result = call_endpoint(
        "GET", f"{BASE_URL}/metrics/",
        description="List all metrics"
    )
    if result:
        log_info(f"   Found {result.get('count', 0)} metrics")

    # Get metric categories
    result = call_endpoint(
        "GET", f"{BASE_URL}/metrics/categories/",
        description="Get metric categories"
    )
    if result:
        log_info(f"   Categories: {result.get('categories', [])}")

    # Get metrics by category
    call_endpoint(
        "GET", f"{BASE_URL}/metrics/by_category/",
        description="Get metrics grouped by category"
    )

    # Get metrics filtered by category
    call_endpoint(
        "GET", f"{BASE_URL}/metrics/by_category/?category=timeseries",
        description="Get timeseries metrics"
    )

    # Get single metric
    call_endpoint(
        "GET", f"{BASE_URL}/metrics/commits_over_time/",
        description="Get commits_over_time metric detail"
    )

    # =========================================================================
    log_header("DATASET ENDPOINTS")
    # =========================================================================

    # List datasets (should be empty or have existing data)
    call_endpoint(
        "GET", f"{BASE_URL}/datasets/",
        description="List all datasets"
    )

    # Upload a dataset
    if SAMPLE_DATA_PATH.exists():
        with open(SAMPLE_DATA_PATH, 'rb') as f:
            result = call_endpoint(
                "POST", f"{BASE_URL}/datasets/upload/",
                data={"workspace_id": "1", "platform": "gitlab"},
                files={"file": ("sample_data.csv", f, "text/csv")},
                expected_status=201,
                description="Upload sample dataset"
            )
            if result:
                dataset_id = result.get('id')
                log_info(f"   Dataset ID: {dataset_id}")
    else:
        log_error(f"Sample data file not found: {SAMPLE_DATA_PATH}")
        return

    if not dataset_id:
        log_error("Cannot continue without a dataset. Exiting.")
        return

    # Get dataset detail
    call_endpoint(
        "GET", f"{BASE_URL}/datasets/{dataset_id}/",
        description="Get dataset detail"
    )

    # Get dataset columns
    result = call_endpoint(
        "GET", f"{BASE_URL}/datasets/{dataset_id}/columns/",
        description="Get dataset columns"
    )
    if result:
        columns = [c.get('name') for c in result.get('columns', [])]
        log_info(f"   Columns: {columns}")

    # Get dataset preview
    result = call_endpoint(
        "GET", f"{BASE_URL}/datasets/{dataset_id}/preview/?rows=5",
        description="Get dataset preview (5 rows)"
    )
    if result:
        log_info(f"   Preview rows: {result.get('preview_rows', 0)} of {result.get('total_rows', 0)}")

    # Get available metrics
    result = call_endpoint(
        "GET", f"{BASE_URL}/datasets/{dataset_id}/available_metrics/",
        description="Get available metrics for dataset"
    )
    if result:
        log_info(f"   Available metrics: {result.get('count', 0)}")
        missing = result.get('missing_columns_by_metric', {})
        if missing:
            log_info(f"   Metrics with missing columns: {list(missing.keys())}")

    # Get compatible axes
    result = call_endpoint(
        "GET", f"{BASE_URL}/datasets/{dataset_id}/compatible_axes/",
        description="Get compatible axes for custom charts"
    )
    if result:
        x_options = [a.get('column') for a in result.get('x_axis', [])]
        y_options = [a.get('column') for a in result.get('y_axis', [])]
        log_info(f"   X-axis options: {x_options}")
        log_info(f"   Y-axis options: {y_options}")

    # =========================================================================
    log_header("GENERATE CHART ENDPOINTS")
    # =========================================================================

    # Generate chart - Mode A: Predefined metric
    result = call_endpoint(
        "POST", f"{BASE_URL}/generate/",
        data={
            "dataset_id": dataset_id,
            "metric_code": "commits_over_time",
            "chart_type": "line",
            "time_aggregation": "M",
            "aggregation": "sum"
        },
        expected_status=201,
        description="Generate commits_over_time chart"
    )
    if result:
        analysis_id = result.get('analysis_id')
        log_info(f"   Analysis ID: {analysis_id}")
        log_info(f"   Chart type: {result.get('chart_type')}")
        chart_data = result.get('chart_data', {})
        labels = chart_data.get('data', {}).get('labels', [])
        log_info(f"   Chart labels: {labels}")
        if result.get('statistics'):
            stats = result.get('statistics')
            log_info(f"   Statistics: total={stats.get('total')}, mean={stats.get('mean'):.2f}")

    # Generate chart - MR Creation Timeline
    call_endpoint(
        "POST", f"{BASE_URL}/generate/",
        data={
            "dataset_id": dataset_id,
            "metric_code": "mr_creation_timeline",
            "chart_type": "bar",
            "time_aggregation": "M"
        },
        expected_status=201,
        description="Generate MR creation timeline"
    )

    # Generate chart - State Distribution (Pie)
    call_endpoint(
        "POST", f"{BASE_URL}/generate/",
        data={
            "dataset_id": dataset_id,
            "metric_code": "state_distribution",
            "chart_type": "pie"
        },
        expected_status=201,
        description="Generate state distribution pie chart"
    )

    # Generate chart - Lead Time Distribution
    call_endpoint(
        "POST", f"{BASE_URL}/generate/",
        data={
            "dataset_id": dataset_id,
            "metric_code": "lead_time_distribution",
            "chart_type": "histogram"
        },
        expected_status=201,
        description="Generate lead time histogram"
    )

    # Generate chart - Mode B: Custom axes
    call_endpoint(
        "POST", f"{BASE_URL}/generate/",
        data={
            "dataset_id": dataset_id,
            "x_axis": "state",
            "y_axis": "#Commits",
            "aggregation": "sum",
            "chart_type": "bar"
        },
        expected_status=201,
        description="Generate custom chart (state vs commits)"
    )

    # Generate chart - Custom scatter
    call_endpoint(
        "POST", f"{BASE_URL}/generate/",
        data={
            "dataset_id": dataset_id,
            "x_axis": "churn_addition",
            "y_axis": "churn_deletions",
            "chart_type": "scatter"
        },
        expected_status=201,
        description="Generate custom scatter plot"
    )

    # Error cases
    call_endpoint(
        "POST", f"{BASE_URL}/generate/",
        data={"metric_code": "commits_over_time"},
        expected_status=400,
        description="Error: Missing dataset_id"
    )

    call_endpoint(
        "POST", f"{BASE_URL}/generate/",
        data={"dataset_id": dataset_id, "metric_code": "invalid_metric"},
        expected_status=404,
        description="Error: Invalid metric code"
    )

    # =========================================================================
    log_header("ANALYSES ENDPOINTS (History)")
    # =========================================================================

    # List all analyses
    result = call_endpoint(
        "GET", f"{BASE_URL}/analyses/",
        description="List all analyses"
    )
    if result:
        log_info(f"   Total analyses: {result.get('count', 0)}")

    # List analyses filtered by dataset
    result = call_endpoint(
        "GET", f"{BASE_URL}/analyses/?dataset_id={dataset_id}",
        description="List analyses for dataset"
    )

    # Bulk create analyses
    result = call_endpoint(
        "POST", f"{BASE_URL}/analyses/bulk_create/",
        data={
            "dataset_id": dataset_id,
            "analyses": [
                {"metric_code": "commits_distribution", "chart_type": "bar"},
                {"metric_code": "discussions_analysis", "chart_type": "bar"},
                {"metric_code": "files_modified", "chart_type": "histogram"}
            ]
        },
        expected_status=201,
        description="Bulk create 3 analyses"
    )
    if result:
        log_info(f"   Created: {result.get('created', 0)} analyses")
        if result.get('errors'):
            log_info(f"   Errors: {result.get('errors')}")

    if analysis_id:
        # Get analysis detail
        call_endpoint(
            "GET", f"{BASE_URL}/analyses/{analysis_id}/",
            description="Get analysis detail"
        )

        # Get analysis result
        result = call_endpoint(
            "GET", f"{BASE_URL}/analyses/{analysis_id}/result/",
            description="Get analysis result"
        )
        if result:
            log_info(f"   Status: {result.get('status')}")
            log_info(f"   Has image: {'Yes' if result.get('image_base64') else 'No'}")

        # Retry analysis
        call_endpoint(
            "POST", f"{BASE_URL}/analyses/{analysis_id}/retry/",
            description="Retry analysis"
        )

    # =========================================================================
    log_header("CLEANUP")
    # =========================================================================

    # Delete the test dataset (also deletes associated analyses)
    call_endpoint(
        "DELETE", f"{BASE_URL}/datasets/{dataset_id}/",
        expected_status=204,
        description="Delete test dataset"
    )

    print()
    log_header("TEST COMPLETE")


if __name__ == "__main__":
    # Parse command line args
    if len(sys.argv) > 1:
        for i, arg in enumerate(sys.argv[1:]):
            if arg == "--base-url" and i + 2 < len(sys.argv):
                BASE_URL = sys.argv[i + 2]

    print(f"{Colors.BOLD}Analytics API Test Suite{Colors.RESET}")
    print(f"Base URL: {BASE_URL}")
    print(f"Sample Data: {SAMPLE_DATA_PATH}")
    
    run_tests()
