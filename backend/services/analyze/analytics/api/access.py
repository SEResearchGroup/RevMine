"""Access helpers for user-scoped analysis resources."""
from __future__ import annotations

import logging
import os
from typing import Iterable

import requests
from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404

from analytics.models import Analysis, Dataset, DevOpsCollectionJob

logger = logging.getLogger(__name__)


def get_request_user_id(request) -> int | None:
    user_id = getattr(request, "user_id", None)
    if user_id is None:
        user_id = request.headers.get("X-User-ID")
    try:
        return int(user_id)
    except (TypeError, ValueError):
        return None


def get_workspace_ids_for_user(user_id: int) -> set[int]:
    base_url = os.getenv(
        "CONFIGURATION_SERVICE_URL",
        "http://configuration-service:8001/api/workspaces",
    ).rstrip("/")
    timeout = float(os.getenv("CONFIGURATION_SERVICE_TIMEOUT", "2"))

    try:
        response = requests.get(
            f"{base_url}/",
            headers={"X-User-ID": str(user_id)},
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Could not resolve workspaces for user %s: %s", user_id, exc)
        return set()

    payload = response.json()
    rows: Iterable[dict]
    if isinstance(payload, dict):
        rows = payload.get("results") or []
    elif isinstance(payload, list):
        rows = payload
    else:
        rows = []

    workspace_ids: set[int] = set()
    for item in rows:
        try:
            workspace_ids.add(int(item["id"]))
        except (KeyError, TypeError, ValueError):
            continue
    return workspace_ids


def filter_dataset_queryset_for_request(queryset: QuerySet, request) -> QuerySet:
    user_id = get_request_user_id(request)
    if user_id is None:
        return queryset.none()

    access_filter = Q(user_id=user_id) | Q(devops_jobs__user_id=user_id)
    workspace_ids = get_workspace_ids_for_user(user_id)
    if workspace_ids:
        access_filter |= Q(user_id__isnull=True, workspace_id__in=workspace_ids)

    return queryset.filter(access_filter).distinct()


def get_dataset_for_request(request, pk) -> Dataset:
    queryset = filter_dataset_queryset_for_request(Dataset.objects.all(), request)
    return get_object_or_404(queryset, pk=pk)


def filter_analysis_queryset_for_request(queryset: QuerySet, request) -> QuerySet:
    datasets = filter_dataset_queryset_for_request(Dataset.objects.all(), request)
    return queryset.filter(dataset_id__in=datasets.values("id")).distinct()


def get_analysis_for_request(request, pk) -> Analysis:
    queryset = filter_analysis_queryset_for_request(Analysis.objects.all(), request)
    return get_object_or_404(queryset, pk=pk)


def get_devops_job_for_request(request, pk) -> DevOpsCollectionJob:
    user_id = get_request_user_id(request)
    queryset = DevOpsCollectionJob.objects.all()
    if user_id is None:
        queryset = queryset.none()
    else:
        queryset = queryset.filter(user_id=user_id)
    return get_object_or_404(queryset, pk=pk)
