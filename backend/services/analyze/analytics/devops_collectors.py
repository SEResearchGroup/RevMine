"""
Live collectors for DevOps datasets (Kanban boards + CI/CD pipelines) against
GitHub and GitLab. Each collector fetches from the provider API with the
user-supplied token and returns a flat pandas DataFrame ready to be persisted
as an analytics Dataset.

These collectors are intentionally small and synchronous so they can run
inside a request. Long-running collections should be moved to Celery once
Kafka topics for the DevOps domain are wired up — the return shape does not
need to change.
"""

from __future__ import annotations

import logging
from typing import Iterable

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


def _session(headers, retries=3):
    s = requests.Session()
    s.headers.update(headers)
    retry = Retry(
        total=retries,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=['GET', 'POST'],
        raise_on_status=False,
    )
    s.mount('https://', HTTPAdapter(max_retries=retry))
    return s


# =============================================================================
# GitHub Actions — CI/CD runs and jobs
# =============================================================================

class GitHubActionsCollector:
    """Pull workflow runs + jobs from GitHub Actions."""

    BASE = 'https://api.github.com'

    def __init__(self, token: str, repo_full_name: str):
        self.repo = repo_full_name
        self.session = _session({
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github+json',
        })

    def list_workflows(self) -> list[dict]:
        resp = self.session.get(
            f'{self.BASE}/repos/{self.repo}/actions/workflows',
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get('workflows', [])

    def _iter_runs(self, since: str | None = None) -> Iterable[dict]:
        page = 1
        while True:
            params = {'per_page': 100, 'page': page}
            if since:
                params['created'] = f'>{since}'
            resp = self.session.get(
                f'{self.BASE}/repos/{self.repo}/actions/runs',
                params=params,
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            runs = data.get('workflow_runs', [])
            if not runs:
                return
            yield from runs
            if len(runs) < 100:
                return
            page += 1

    def _iter_jobs_for_run(self, run_id: int) -> Iterable[dict]:
        page = 1
        while True:
            resp = self.session.get(
                f'{self.BASE}/repos/{self.repo}/actions/runs/{run_id}/jobs',
                params={'per_page': 100, 'page': page},
                timeout=60,
            )
            if resp.status_code != 200:
                return
            data = resp.json()
            jobs = data.get('jobs', [])
            if not jobs:
                return
            yield from jobs
            if len(jobs) < 100:
                return
            page += 1

    def collect(self, since: str | None = None, max_runs: int = 500) -> pd.DataFrame:
        rows: list[dict] = []
        collected = 0
        for run in self._iter_runs(since=since):
            if collected >= max_runs:
                break
            collected += 1
            run_id = run.get('id')
            created_at = run.get('created_at')
            started_at = run.get('run_started_at') or created_at
            updated_at = run.get('updated_at')
            duration_s = None
            if started_at and updated_at:
                try:
                    duration_s = (
                        pd.to_datetime(updated_at) - pd.to_datetime(started_at)
                    ).total_seconds()
                except Exception:
                    duration_s = None
            for job in self._iter_jobs_for_run(run_id):
                rows.append({
                    'run_id': run_id,
                    'job_id': job.get('id'),
                    'job_name': job.get('name'),
                    'workflow_name': run.get('name'),
                    'conclusion': job.get('conclusion') or run.get('conclusion'),
                    'status': job.get('status') or run.get('status'),
                    'branch': run.get('head_branch'),
                    'sha': run.get('head_sha'),
                    'actor': (run.get('actor') or {}).get('login'),
                    'runner_name': job.get('runner_name') or 'github-hosted',
                    'created_at': job.get('created_at') or created_at,
                    'started_at': job.get('started_at') or started_at,
                    'completed_at': job.get('completed_at') or updated_at,
                    'duration_s': duration_s,
                })
        return pd.DataFrame(rows)


# =============================================================================
# GitHub Projects v2 — Kanban board items
# =============================================================================

class GitHubProjectsCollector:
    """Pull Projects v2 items + their status field via GraphQL."""

    GRAPHQL = 'https://api.github.com/graphql'

    LIST_PROJECTS_QUERY = """
    query($owner: String!) {
      user(login: $owner) { projectsV2(first: 20) { nodes { id number title } } }
      organization(login: $owner) { projectsV2(first: 20) { nodes { id number title } } }
    }
    """

    ITEMS_QUERY = """
    query($projectId: ID!, $cursor: String) {
      node(id: $projectId) {
        ... on ProjectV2 {
          items(first: 100, after: $cursor) {
            pageInfo { hasNextPage endCursor }
            nodes {
              id
              createdAt
              updatedAt
              content {
                ... on Issue {
                  title state createdAt closedAt
                  author { login }
                  assignees(first: 10) { nodes { login } }
                  labels(first: 20) { nodes { name } }
                }
                ... on PullRequest {
                  title state createdAt closedAt mergedAt
                  author { login }
                  assignees(first: 10) { nodes { login } }
                  labels(first: 20) { nodes { name } }
                }
              }
              fieldValues(first: 20) {
                nodes {
                  ... on ProjectV2ItemFieldSingleSelectValue {
                    name
                    field { ... on ProjectV2FieldCommon { name } }
                  }
                }
              }
            }
          }
        }
      }
    }
    """

    def __init__(self, token: str):
        self.session = _session({
            'Authorization': f'bearer {token}',
            'Accept': 'application/vnd.github+json',
        })

    def _graphql(self, query: str, variables: dict):
        resp = self.session.post(
            self.GRAPHQL, json={'query': query, 'variables': variables}, timeout=60
        )
        resp.raise_for_status()
        payload = resp.json()
        if 'errors' in payload:
            raise RuntimeError(payload['errors'])
        return payload['data']

    def list_projects(self, owner: str) -> list[dict]:
        try:
            data = self._graphql(self.LIST_PROJECTS_QUERY, {'owner': owner})
        except Exception as exc:
            logger.warning('Projects v2 listing failed for %s: %s', owner, exc)
            return []
        projects = []
        for root_key in ('user', 'organization'):
            root = data.get(root_key) or {}
            nodes = (root.get('projectsV2') or {}).get('nodes') or []
            projects.extend(nodes)
        return projects

    def collect_board(self, project_node_id: str) -> pd.DataFrame:
        rows: list[dict] = []
        cursor = None
        while True:
            data = self._graphql(
                self.ITEMS_QUERY,
                {'projectId': project_node_id, 'cursor': cursor},
            )
            items = (((data or {}).get('node') or {}).get('items') or {})
            for node in items.get('nodes', []) or []:
                content = node.get('content') or {}
                status = None
                for fv in ((node.get('fieldValues') or {}).get('nodes') or []):
                    field_name = ((fv or {}).get('field') or {}).get('name', '')
                    if field_name.lower() == 'status':
                        status = fv.get('name')
                        break
                rows.append({
                    'issue_id': node.get('id'),
                    'title': content.get('title'),
                    'status': status or content.get('state'),
                    'column': status or content.get('state'),
                    'created_at': content.get('createdAt') or node.get('createdAt'),
                    'closed_at': content.get('closedAt'),
                    'assignee': ','.join(
                        (a.get('login') for a in (content.get('assignees') or {}).get('nodes', []) if a.get('login'))
                    ),
                    'author': (content.get('author') or {}).get('login'),
                    'labels': ','.join(
                        (l.get('name') for l in (content.get('labels') or {}).get('nodes', []) if l.get('name'))
                    ),
                    # Fields downstream metrics key off — populated opportunistically.
                    'in_progress_at': None,
                    'done_at': content.get('closedAt'),
                    'entered_at': content.get('createdAt') or node.get('createdAt'),
                    'left_at': content.get('closedAt'),
                    'date': content.get('createdAt') or node.get('createdAt'),
                    'duration_h': None,
                })
                if rows[-1]['entered_at'] and rows[-1]['left_at']:
                    try:
                        delta = (
                            pd.to_datetime(rows[-1]['left_at'])
                            - pd.to_datetime(rows[-1]['entered_at'])
                        )
                        rows[-1]['duration_h'] = delta.total_seconds() / 3600
                    except Exception:
                        pass
            if not items.get('pageInfo', {}).get('hasNextPage'):
                break
            cursor = items['pageInfo']['endCursor']
        return pd.DataFrame(rows)


# =============================================================================
# GitLab CI — pipelines + jobs
# =============================================================================

class GitLabCICollector:
    def __init__(self, token: str, project_id: int, base_url: str = 'https://gitlab.com'):
        self.project_id = project_id
        self.base_url = base_url.rstrip('/')
        self.session = _session({
            'PRIVATE-TOKEN': token,
            'Accept': 'application/json',
        })

    def _url(self, suffix: str) -> str:
        return f'{self.base_url}/api/v4/projects/{self.project_id}/{suffix.lstrip("/")}'

    def list_pipelines_page(self, page: int = 1, per_page: int = 50) -> list[dict]:
        resp = self.session.get(
            self._url('pipelines'),
            params={'per_page': per_page, 'page': page},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def _iter_jobs(self, pipeline_id: int) -> Iterable[dict]:
        page = 1
        while True:
            resp = self.session.get(
                self._url(f'pipelines/{pipeline_id}/jobs'),
                params={'per_page': 100, 'page': page},
                timeout=30,
            )
            if resp.status_code != 200:
                return
            data = resp.json() or []
            if not data:
                return
            yield from data
            if len(data) < 100:
                return
            page += 1

    def collect(self, max_pipelines: int = 300) -> pd.DataFrame:
        rows: list[dict] = []
        page = 1
        collected = 0
        while collected < max_pipelines:
            pipelines = self.list_pipelines_page(page=page)
            if not pipelines:
                break
            for pipeline in pipelines:
                if collected >= max_pipelines:
                    break
                collected += 1
                pid = pipeline.get('id')
                for job in self._iter_jobs(pid):
                    created_at = job.get('created_at')
                    started_at = job.get('started_at') or created_at
                    finished_at = job.get('finished_at')
                    duration = job.get('duration')
                    rows.append({
                        'run_id': pid,
                        'job_id': job.get('id'),
                        'job_name': job.get('name'),
                        'workflow_name': job.get('stage') or pipeline.get('name'),
                        'conclusion': job.get('status'),
                        'status': job.get('status'),
                        'branch': pipeline.get('ref'),
                        'sha': pipeline.get('sha'),
                        'actor': (job.get('user') or {}).get('username'),
                        'runner_name': (job.get('runner') or {}).get('description') or 'gitlab-shared',
                        'created_at': created_at,
                        'started_at': started_at,
                        'completed_at': finished_at,
                        'duration_s': float(duration) if duration is not None else None,
                    })
            if len(pipelines) < 50:
                break
            page += 1
        return pd.DataFrame(rows)


# =============================================================================
# GitLab Issue Boards — issues with column history
# =============================================================================

class GitLabBoardsCollector:
    def __init__(self, token: str, project_id: int, base_url: str = 'https://gitlab.com'):
        self.project_id = project_id
        self.base_url = base_url.rstrip('/')
        self.session = _session({
            'PRIVATE-TOKEN': token,
            'Accept': 'application/json',
        })

    def _url(self, suffix: str) -> str:
        return f'{self.base_url}/api/v4/projects/{self.project_id}/{suffix.lstrip("/")}'

    def list_boards(self) -> list[dict]:
        resp = self.session.get(self._url('boards'), timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _iter_issues(self) -> Iterable[dict]:
        page = 1
        while True:
            resp = self.session.get(
                self._url('issues'),
                params={'per_page': 100, 'page': page, 'scope': 'all'},
                timeout=30,
            )
            if resp.status_code != 200:
                return
            data = resp.json() or []
            if not data:
                return
            yield from data
            if len(data) < 100:
                return
            page += 1

    def collect(self) -> pd.DataFrame:
        rows: list[dict] = []
        for issue in self._iter_issues():
            labels = issue.get('labels') or []
            created = issue.get('created_at')
            closed = issue.get('closed_at')
            duration_h = None
            if created and closed:
                try:
                    duration_h = (
                        pd.to_datetime(closed) - pd.to_datetime(created)
                    ).total_seconds() / 3600
                except Exception:
                    duration_h = None
            status = issue.get('state')
            # GitLab issue boards expose a "label-based column" model — the first
            # workflow label (if any) is the active column.
            column = status
            for lbl in labels:
                if '::' in lbl or lbl.lower().startswith('doing') or lbl.lower().startswith('wip'):
                    column = lbl
                    break
            rows.append({
                'issue_id': issue.get('id'),
                'title': issue.get('title'),
                'status': status,
                'column': column,
                'created_at': created,
                'closed_at': closed,
                'assignee': (issue.get('assignee') or {}).get('username'),
                'author': (issue.get('author') or {}).get('username'),
                'labels': ','.join(labels),
                'in_progress_at': None,
                'done_at': closed,
                'entered_at': created,
                'left_at': closed,
                'date': created,
                'duration_h': duration_h,
            })
        return pd.DataFrame(rows)
