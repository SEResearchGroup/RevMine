"""
DRF views for DevOps (Kanban + CI/CD) live collection and dataset creation.

All endpoints accept the provider token in the request body — the frontend
already has it from the GitHub/GitLab OAuth flow. If you later front this with
the Kafka-based workspace-token service, swap the `token = data['token']` line
for `resolve_workspace_token(...)`.
"""

import io
import json
import logging
import os
import uuid

import pandas as pd
from django.conf import settings
from django.core.files.storage import default_storage
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

import re as _re

from analytics.services.dataset_service import DatasetService
from analytics.infrastructure.collectors.devops_collectors import (
    GitHubActionsCollector,
    GitHubProjectsCollector,
    GitLabBoardsCollector,
    GitLabCICollector,
)
from analytics.infrastructure.tasks.devops_tasks import start_job
from analytics.models import Dataset, DevOpsCollectionJob
from analytics.api.serializers import DatasetSerializer
from analytics.workspace_tokens import WorkspaceTokenError, resolve_workspace_token

logger = logging.getLogger(__name__)


def _resolve_token(request, data):
    """
    Shared token-resolution helper. Returns (token, platform) or raises
    ValueError describing why the request is missing credentials.

    Priority:
      1. Explicit 'token' in the body (manual paste flow).
      2. 'workspace_id' → resolve via Kafka request-reply against the
         configuration service (uses the user's stored OAuth token).
    """
    token = data.get('token')
    if token:
        return token, (data.get('provider') or '').lower() or None

    workspace_id = data.get('workspace_id')
    if not workspace_id:
        raise ValueError('Provide either a token or a workspace_id.')

    user_id = getattr(request, 'user_id', None)
    if not user_id:
        raise ValueError('Authenticated user required to resolve workspace token.')

    try:
        resolved = resolve_workspace_token(int(user_id), int(workspace_id))
    except WorkspaceTokenError as exc:
        raise ValueError(str(exc)) from exc
    return resolved['token'], resolved.get('platform')


class KanbanListBoardsView(APIView):
    """
    POST /devops/kanban/boards/
    Body (one of):
      { provider, token, owner? (gh), project_id? (gl), base_url? (gl) }
      { provider, workspace_id, owner? (gh), project_id? (gl), base_url? (gl) }
    """

    def post(self, request):
        data = request.data or {}
        provider = (data.get('provider') or '').lower()
        if not provider:
            return Response(
                {'error': 'provider is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token, resolved_provider = _resolve_token(request, data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        provider = provider or (resolved_provider or '').lower()

        try:
            if provider == 'github':
                owner = data.get('owner')
                if not owner:
                    return Response(
                        {'error': 'owner is required for github.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                projects = GitHubProjectsCollector(token).list_projects(owner)
                return Response({'boards': [
                    {'id': p.get('id'), 'number': p.get('number'), 'title': p.get('title')}
                    for p in projects
                ]})
            if provider == 'gitlab':
                project_id = data.get('project_id')
                if not project_id:
                    return Response(
                        {'error': 'project_id is required for gitlab.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                base_url = data.get('base_url') or 'https://gitlab.com'
                boards = GitLabBoardsCollector(token, project_id, base_url).list_boards()
                return Response({'boards': [
                    {'id': b.get('id'), 'title': b.get('name')}
                    for b in boards
                ]})
            return Response(
                {'error': f'Unsupported provider: {provider}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.exception('Failed to list kanban boards')
            return Response(
                {'error': f'Provider request failed: {exc}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class CICDListPipelinesView(APIView):
    """
    POST /devops/cicd/pipelines/
    Body (one of):
      { provider: 'github', token,        repo_full_name }
      { provider: 'github', workspace_id, repo_full_name }
      { provider: 'gitlab', token,        project_id, base_url? }
      { provider: 'gitlab', workspace_id, project_id, base_url? }
    """

    def post(self, request):
        data = request.data or {}
        provider = (data.get('provider') or '').lower()
        if not provider:
            return Response(
                {'error': 'provider is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token, resolved_provider = _resolve_token(request, data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        provider = provider or (resolved_provider or '').lower()

        try:
            if provider == 'github':
                repo = data.get('repo_full_name')
                if not repo:
                    return Response(
                        {'error': 'repo_full_name is required for github.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                workflows = GitHubActionsCollector(token, repo).list_workflows()
                return Response({'pipelines': [
                    {'id': w.get('id'), 'name': w.get('name'), 'state': w.get('state'), 'path': w.get('path')}
                    for w in workflows
                ]})
            if provider == 'gitlab':
                project_id = data.get('project_id')
                if not project_id:
                    return Response(
                        {'error': 'project_id is required for gitlab.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                base_url = data.get('base_url') or 'https://gitlab.com'
                pipelines = GitLabCICollector(token, project_id, base_url).list_pipelines_page(page=1)
                return Response({'pipelines': [
                    {'id': p.get('id'), 'status': p.get('status'), 'ref': p.get('ref'), 'sha': p.get('sha')}
                    for p in pipelines
                ]})
            return Response(
                {'error': f'Unsupported provider: {provider}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.exception('Failed to list pipelines')
            return Response(
                {'error': f'Provider request failed: {exc}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class KanbanCollectView(APIView):
    """
    POST /devops/kanban/collect/
    Kicks off an async background collection. Returns 202 with a job_id the
    frontend can poll via /devops/jobs/<id>/status/. On completion the worker
    publishes a Kafka notification so the WebSocket-based notification
    service notifies the user even if they navigate away.

    Body (one of):
      { provider, token,        board_id, ... }
      { provider, workspace_id, board_id, ... }
      Extra: project_id (gl), owner (gh), base_url (gl), repository_id?, name?
    """

    def post(self, request):
        data = request.data or {}
        provider = (data.get('provider') or '').lower()
        board_id = data.get('board_id')
        if not provider or not board_id:
            return Response(
                {'error': 'provider and board_id are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token, resolved_provider = _resolve_token(request, data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        provider = provider or (resolved_provider or '').lower()
        if provider not in ('github', 'gitlab'):
            return Response(
                {'error': f'Unsupported provider: {provider}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if provider == 'gitlab' and not data.get('project_id'):
            return Response(
                {'error': 'project_id is required for gitlab.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        job = _create_job(
            request=request,
            data=data,
            source_type='kanban',
            provider=provider,
            label=str(data.get('name') or board_id),
        )
        start_job(job, token)
        return Response(_serialize_job(job), status=status.HTTP_202_ACCEPTED)


class CICDCollectView(APIView):
    """
    POST /devops/cicd/collect/
    Same async pattern as KanbanCollectView — returns a job_id immediately.

    Body (one of):
      { provider, token,        repo_full_name? (gh) / project_id? (gl), ... }
      { provider, workspace_id, repo_full_name? (gh) / project_id? (gl), ... }
      Extras: base_url (gl), repository_id, since, max_runs, name
    """

    def post(self, request):
        data = request.data or {}
        provider = (data.get('provider') or '').lower()
        if not provider:
            return Response(
                {'error': 'provider is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token, resolved_provider = _resolve_token(request, data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        provider = provider or (resolved_provider or '').lower()
        if provider not in ('github', 'gitlab'):
            return Response(
                {'error': f'Unsupported provider: {provider}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if provider == 'github' and not data.get('repo_full_name'):
            return Response(
                {'error': 'repo_full_name is required for github.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if provider == 'gitlab' and not data.get('project_id'):
            return Response(
                {'error': 'project_id is required for gitlab.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        identifier = data.get('repo_full_name') or str(data.get('project_id') or '')
        job = _create_job(
            request=request,
            data=data,
            source_type='cicd',
            provider=provider,
            label=str(data.get('name') or identifier),
        )
        start_job(job, token)
        return Response(_serialize_job(job), status=status.HTTP_202_ACCEPTED)


class DevOpsJobStatusView(APIView):
    """
    GET /devops/jobs/<uuid:pk>/status/
    Polled by the frontend progress page. Returns status + progress percent +
    message + dataset reference once completed.
    """

    def get(self, request, pk):
        job = get_object_or_404(DevOpsCollectionJob, pk=pk)
        return Response(_serialize_job(job))


def _create_job(request, data, source_type, provider, label):
    """
    Persist a DevOpsCollectionJob row from the inbound request. Strips out
    secrets — the access token is passed straight to the worker thread and
    NEVER stored on the job row.
    """
    safe_payload = {k: v for k, v in (data or {}).items() if k != 'token'}
    user_id = getattr(request, 'user_id', None)
    workspace_id = data.get('workspace_id')
    repository_id = data.get('repository_id')

    return DevOpsCollectionJob.objects.create(
        user_id=int(user_id) if user_id else None,
        workspace_id=int(workspace_id) if workspace_id else None,
        repository_id=int(repository_id) if repository_id else None,
        source_type=source_type,
        provider=provider,
        label=label[:255] if label else '',
        request_payload=safe_payload,
        status='pending',
        progress_percent=0,
        progress_message='Queued',
    )


def _serialize_job(job: DevOpsCollectionJob) -> dict:
    return {
        'id': str(job.id),
        'source_type': job.source_type,
        'provider': job.provider,
        'label': job.label,
        'status': job.status,
        'progress_percent': job.progress_percent,
        'progress_message': job.progress_message,
        'collected_items': job.collected_items,
        'total_items': job.total_items,
        'error_message': job.error_message or None,
        'workspace_id': job.workspace_id,
        'repository_id': job.repository_id,
        'dataset': DatasetSerializer(job.dataset).data if job.dataset else None,
        'created_at': job.created_at.isoformat() if job.created_at else None,
        'started_at': job.started_at.isoformat() if job.started_at else None,
        'completed_at': job.completed_at.isoformat() if job.completed_at else None,
    }


def _locate_dataset_file(dataset):
    """
    Return (resolved_path, raw_bytes) for the dataset's CSV, or raise
    FileNotFoundError if we truly cannot find it.

    Resolution order:
      1. DB-stored file_path via default_storage.
      2. DB-stored file_path with both / and \\ separators normalised against
         MEDIA_ROOT (handles rows written on a different OS).
      3. Scan MEDIA_ROOT/datasets/ for a file whose name shares the UUID
         prefix or the dataset.filename suffix. Self-heals old rows whose
         file_path in DB no longer matches what's on disk.
    """
    file_path = dataset.file_path or ''
    media_root = getattr(settings, 'MEDIA_ROOT', None)
    storage_subdir = getattr(settings, 'DATASET_STORAGE_PATH', 'datasets/') or 'datasets/'

    # Step 1: DB path as-is via default_storage.
    if file_path:
        try:
            if default_storage.exists(file_path):
                with default_storage.open(file_path, 'rb') as fh:
                    return file_path, fh.read()
        except Exception as exc:
            logger.warning('default_storage read failed for %s: %s', file_path, exc)

    # Step 2: try absolute path with normalised separators.
    if file_path and media_root:
        for variant in {
            file_path,
            file_path.replace('\\', '/'),
            file_path.replace('/', os.sep),
        }:
            abs_candidate = variant if os.path.isabs(variant) else os.path.join(media_root, variant)
            if os.path.isfile(abs_candidate):
                with open(abs_candidate, 'rb') as fh:
                    return abs_candidate, fh.read()

    # Step 3: scan MEDIA_ROOT/datasets for something close.
    if not media_root:
        raise FileNotFoundError(f'Dataset file not found: {file_path}')

    basename = os.path.basename((file_path or '').replace('\\', '/'))
    # uuid prefix written in create_dataset_from_dataframe is the UUID4 + '_'.
    prefix = basename.split('_', 1)[0] if basename else ''
    search_root = os.path.join(media_root, storage_subdir)

    if not os.path.isdir(search_root):
        raise FileNotFoundError(
            f'Dataset file not found: {file_path} (storage dir missing: {search_root})'
        )

    candidates = []
    for root, _dirs, files in os.walk(search_root):
        for name in files:
            if not name.lower().endswith('.csv'):
                continue
            abs_path = os.path.join(root, name)
            if prefix and (name.startswith(prefix) or prefix in name):
                candidates.append(abs_path)
            elif dataset.filename and dataset.filename in name:
                candidates.append(abs_path)

    if not candidates:
        raise FileNotFoundError(
            f'Dataset file not found: {file_path} (no matches in {search_root})'
        )

    abs_match = candidates[0]
    with open(abs_match, 'rb') as fh:
        return abs_match, fh.read()


class DevOpsDatasetDownloadView(APIView):
    """
    GET /devops/datasets/<uuid:pk>/download/?format=csv|json|debug
    CSV / JSON return the dataset as a downloadable file. The `debug` format
    returns a JSON blob describing where we looked — use this to diagnose
    "not found" errors.
    """

    def get(self, request, pk):
        dataset = get_object_or_404(Dataset, pk=pk)
        if dataset.source_type not in ('kanban', 'cicd'):
            return Response(
                {'error': f'This endpoint only serves kanban / cicd datasets '
                          f'(this one is "{dataset.source_type}").'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        fmt = (request.query_params.get('format') or 'csv').lower()
        if fmt not in ('csv', 'json', 'debug'):
            return Response(
                {'error': 'format must be "csv", "json", or "debug".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if fmt == 'debug':
            media_root = getattr(settings, 'MEDIA_ROOT', None)
            file_path = dataset.file_path or ''
            abs_expected = os.path.join(media_root, file_path) if media_root else None
            storage_subdir = getattr(settings, 'DATASET_STORAGE_PATH', 'datasets/')
            search_root = os.path.join(media_root, storage_subdir) if media_root else None
            listing = []
            if search_root and os.path.isdir(search_root):
                for root, _dirs, files in os.walk(search_root):
                    for name in files:
                        listing.append(os.path.relpath(os.path.join(root, name), media_root))
                listing = sorted(listing)[:50]
            return Response({
                'dataset_id': str(dataset.id),
                'filename': dataset.filename,
                'file_path': file_path,
                'expected_abs_path': abs_expected,
                'expected_exists': bool(abs_expected and os.path.exists(abs_expected)),
                'media_root': media_root,
                'storage_subdir': storage_subdir,
                'files_in_storage_sample': listing,
            })

        try:
            resolved_path, raw_bytes = _locate_dataset_file(dataset)
        except FileNotFoundError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            logger.exception('Unexpected error reading dataset %s', dataset.id)
            return Response(
                {'error': f'Failed to read dataset file: {exc}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(
            'DevOps download: dataset=%s fmt=%s resolved_path=%s bytes=%d',
            dataset.id, fmt, resolved_path, len(raw_bytes),
        )

        raw_base = (dataset.filename or f'dataset_{dataset.id}').rsplit('.', 1)[0]
        base_name = DatasetService.sanitize_filename(raw_base) or f'dataset_{dataset.id}'

        # Both CSV and JSON re-emit the data via pandas. This guarantees
        # symmetric behaviour between the two formats: if JSON succeeds,
        # CSV cannot fail on bytes/encoding quirks (trailing NULLs, BOM,
        # mixed line endings, non-UTF-8 cells). It also lets us normalise
        # date columns to ISO-8601 in both outputs.
        try:
            df = pd.read_csv(io.BytesIO(raw_bytes))
        except Exception as exc:
            logger.exception('Failed to parse stored CSV for dataset %s', dataset.id)
            return Response(
                {'error': f'Stored CSV is malformed: {exc}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if fmt == 'csv':
            buf = io.StringIO()
            df.to_csv(buf, index=False)
            payload_bytes = buf.getvalue().encode('utf-8')
            response = HttpResponse(payload_bytes, content_type='text/csv')
            response['Content-Disposition'] = (
                f'attachment; filename="{base_name}.csv"'
            )
            response['Content-Length'] = str(len(payload_bytes))
            return response

        # JSON
        payload = df.to_json(orient='records', date_format='iso')
        response = HttpResponse(payload, content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="{base_name}.json"'
        response['Content-Length'] = str(len(payload))
        return response


class DevOpsComputeMetricsView(APIView):
    """
    POST /devops/datasets/<uuid:pk>/compute-metrics/
    Body: { "metric_codes": ["kanban_lead_time", "kanban_throughput", ...] }

    Runs each requested metric against the dataset (in-memory, not persisted
    to the analyses table) and returns a flat list of statistics so the
    frontend can preview them and offer a CSV download. Use the GET version
    of this endpoint with `format=csv` to download the same data as a CSV.
    """

    def post(self, request, pk):
        dataset = get_object_or_404(Dataset, pk=pk)
        if dataset.source_type not in ('kanban', 'cicd'):
            return Response(
                {'error': 'compute-metrics only supports kanban / cicd datasets.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        codes = request.data.get('metric_codes') or []
        if not isinstance(codes, list) or not codes:
            return Response(
                {'error': 'metric_codes must be a non-empty list.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            rows = _compute_metric_rows(dataset, codes)
        except Exception as exc:
            logger.exception('compute-metrics failed for dataset %s', dataset.id)
            return Response(
                {'error': f'Compute failed: {exc}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response({
            'dataset_id': str(dataset.id),
            'metric_codes': codes,
            'rows': rows,
        })


class DevOpsComputeMetricsCSVView(APIView):
    """
    POST /devops/datasets/<uuid:pk>/compute-metrics/csv/
    Same body as DevOpsComputeMetricsView. Streams the computed statistics
    back as a CSV download.
    """

    def post(self, request, pk):
        dataset = get_object_or_404(Dataset, pk=pk)
        if dataset.source_type not in ('kanban', 'cicd'):
            return Response(
                {'error': 'compute-metrics only supports kanban / cicd datasets.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        codes = request.data.get('metric_codes') or []
        if not isinstance(codes, list) or not codes:
            return Response(
                {'error': 'metric_codes must be a non-empty list.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            rows = _compute_metric_rows(dataset, codes)
        except Exception as exc:
            logger.exception('compute-metrics csv failed for dataset %s', dataset.id)
            return Response(
                {'error': f'Compute failed: {exc}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        df = pd.DataFrame(rows, columns=['metric_code', 'metric_name', 'statistic', 'value'])
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        payload = buf.getvalue().encode('utf-8')

        raw_base = (dataset.filename or f'dataset_{dataset.id}').rsplit('.', 1)[0]
        base_name = DatasetService.sanitize_filename(raw_base) or f'dataset_{dataset.id}'
        response = HttpResponse(payload, content_type='text/csv')
        response['Content-Disposition'] = (
            f'attachment; filename="{base_name}_metrics.csv"'
        )
        response['Content-Length'] = str(len(payload))
        return response


def _compute_metric_rows(dataset, codes):
    """
    Run the analysis function for each metric code against the dataset and
    return a flat list of {metric_code, metric_name, statistic, value}.
    Errors per metric are captured as a single row with statistic="error".
    """
    from .analysis_service import AnalysisService
    from .models import Analysis, MetricDefinition

    service = DatasetService()
    df = service.load_dataframe(dataset)

    analysis_service = AnalysisService()
    df = analysis_service._parse_dates(df)

    metrics_by_code = {
        m.code: m for m in MetricDefinition.objects.filter(code__in=codes, is_active=True)
    }

    rows = []
    for code in codes:
        metric = metrics_by_code.get(code)
        metric_name = metric.name if metric else code

        function_name = metric.analysis_function if metric else code
        fn = analysis_service.function_mapping.get(function_name)
        if not fn:
            rows.append({
                'metric_code': code,
                'metric_name': metric_name,
                'statistic': 'error',
                'value': f'no analysis function for "{function_name}"',
            })
            continue

        # Build a transient Analysis (NOT saved) so existing functions can read
        # its config dict without DB writes.
        transient = Analysis(
            dataset=dataset,
            metric_code=code,
            chart_type=(metric.default_chart_type if metric else 'bar'),
            config={},
        )

        try:
            result = fn(df, transient)
            stats = (result or {}).get('statistics') or {}
            stats = analysis_service._sanitize_value(stats)
            flat = _flatten_stats(stats)
            if not flat:
                rows.append({
                    'metric_code': code,
                    'metric_name': metric_name,
                    'statistic': 'value',
                    'value': '',
                })
                continue
            for stat_name, value in flat:
                rows.append({
                    'metric_code': code,
                    'metric_name': metric_name,
                    'statistic': stat_name,
                    'value': value,
                })
        except Exception as exc:
            rows.append({
                'metric_code': code,
                'metric_name': metric_name,
                'statistic': 'error',
                'value': str(exc),
            })

    return rows


def _flatten_stats(stats, prefix=''):
    """Flatten nested statistics dicts into [(key, value), ...] pairs."""
    out = []
    if not isinstance(stats, dict):
        out.append((prefix or 'value', stats))
        return out
    for k, v in stats.items():
        key = f'{prefix}.{k}' if prefix else str(k)
        if isinstance(v, dict):
            out.extend(_flatten_stats(v, key))
        elif isinstance(v, (list, tuple)):
            # Keep list as a single value if small primitives; otherwise skip
            # to avoid blowing up the CSV.
            if all(isinstance(x, (int, float, str, bool)) or x is None for x in v) and len(v) <= 25:
                out.append((key, ', '.join(str(x) for x in v)))
            else:
                out.append((key, f'[{len(v)} items]'))
        else:
            out.append((key, v))
    return out


class DevOpsDatasetsView(APIView):
    """
    GET /devops/datasets/?source_type=kanban|cicd
    Convenience endpoint — just a filtered view of the datasets list used by
    the kanban/cicd history pages.
    """

    def get(self, request):
        source_type = (request.query_params.get('source_type') or '').lower()
        if source_type not in ('kanban', 'cicd'):
            return Response(
                {'error': 'source_type must be "kanban" or "cicd".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        queryset = Dataset.objects.filter(source_type=source_type).order_by('-uploaded_at')
        return Response({
            'count': queryset.count(),
            'results': DatasetSerializer(queryset, many=True).data,
        })
