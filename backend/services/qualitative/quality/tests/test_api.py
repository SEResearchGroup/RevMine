from unittest.mock import patch

import pytest

from quality.infrastructure.etl.builder import build_dataset
from quality.models import QualitativeDataset
from quality.services.dataset_service import DatasetService


@pytest.fixture
def ready_dataset(make_dataset, github_data):
    dataset = make_dataset(platform="github", status="ready")
    stats = build_dataset(dataset, github_data)
    dataset.stats = stats
    dataset.save()
    return dataset


@pytest.mark.django_db
class TestDatasetApi:
    def test_list_datasets_scoped_to_user(self, api_client, ready_dataset, make_dataset):
        make_dataset(platform="github", user_id=999)  # other user's dataset
        resp = api_client.get("/api/v1/qualitative/datasets/")
        assert resp.status_code == 200
        ids = [d["id"] for d in resp.json()["datasets"]]
        assert str(ready_dataset.id) in ids
        assert len(ids) == 1

    def test_dataset_detail_has_stats(self, api_client, ready_dataset):
        resp = api_client.get(f"/api/v1/qualitative/datasets/{ready_dataset.id}/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ready"
        assert body["stats"]["comments_human"] == 4

    def test_requires_user_header(self, ready_dataset):
        from rest_framework.test import APIClient
        resp = APIClient().get("/api/v1/qualitative/datasets/")
        assert resp.status_code == 400


@pytest.mark.django_db
class TestCommentApi:
    def test_list_human_only_by_default(self, api_client, ready_dataset):
        resp = api_client.get(f"/api/v1/qualitative/datasets/{ready_dataset.id}/comments/")
        assert resp.status_code == 200
        assert resp.json()["count"] == 4  # bot comment excluded

    def test_include_non_human(self, api_client, ready_dataset):
        resp = api_client.get(
            f"/api/v1/qualitative/datasets/{ready_dataset.id}/comments/?include_non_human=true"
        )
        assert resp.json()["count"] == 5

    def test_filter_by_type(self, api_client, ready_dataset):
        resp = api_client.get(
            f"/api/v1/qualitative/datasets/{ready_dataset.id}/comments/?type=inline"
        )
        assert resp.json()["count"] == 2

    def test_search_q(self, api_client, ready_dataset):
        resp = api_client.get(
            f"/api/v1/qualitative/datasets/{ready_dataset.id}/comments/?q=mutex"
        )
        results = resp.json()["results"]
        assert len(results) == 1 and "mutex" in results[0]["body_excerpt"]

    def test_filter_by_author(self, api_client, ready_dataset):
        resp = api_client.get(
            f"/api/v1/qualitative/datasets/{ready_dataset.id}/comments/?author=alice"
        )
        assert resp.json()["count"] == 1  # alice's inline reply

    def test_filter_by_role_reviewer(self, api_client, ready_dataset):
        resp = api_client.get(
            f"/api/v1/qualitative/datasets/{ready_dataset.id}/comments/?role=reviewer"
        )
        # bob's general + review_summary + inline = 3 (alice's author-role reply excluded)
        assert resp.json()["count"] == 3
        assert all(c["author_role"] == "reviewer" for c in resp.json()["results"])

    def test_filter_by_role_author(self, api_client, ready_dataset):
        resp = api_client.get(
            f"/api/v1/qualitative/datasets/{ready_dataset.id}/comments/?role=author"
        )
        assert resp.json()["count"] == 1

    def test_facets_split_by_role(self, api_client, ready_dataset):
        resp = api_client.get(f"/api/v1/qualitative/datasets/{ready_dataset.id}/facets/")
        body = resp.json()
        assert body["reviewers"] == ["bob"]   # reviewed others' change
        assert body["authors"] == ["alice"]   # the PR author
        assert "inline" in body["types"] and "general" in body["types"]

    def test_timeseries_granularities(self, api_client, ready_dataset):
        for g in ("day", "week", "month"):
            resp = api_client.get(
                f"/api/v1/qualitative/datasets/{ready_dataset.id}/timeseries/?granularity={g}"
            )
            assert resp.status_code == 200
            assert resp.json()["granularity"] == g
            assert sum(p["count"] for p in resp.json()["series"]) == 4  # human comments

    def test_timeseries_role_filter(self, api_client, ready_dataset):
        resp = api_client.get(
            f"/api/v1/qualitative/datasets/{ready_dataset.id}/timeseries/?role=reviewer&granularity=day"
        )
        assert sum(p["count"] for p in resp.json()["series"]) == 3

    def test_comment_detail(self, api_client, ready_dataset):
        from quality.models import Comment
        c = Comment.objects.get(dataset=ready_dataset, external_id="11")
        resp = api_client.get(
            f"/api/v1/qualitative/datasets/{ready_dataset.id}/comments/{c.id}/"
        )
        body = resp.json()
        assert body["body"] == "why mutex?"
        assert body["review"]["number"] == 1
        assert body["thread"]["is_resolved"] is True
        assert len(body["thread"]["comments"]) == 2


@pytest.mark.django_db
class TestStartAnalysis:
    def test_queues_when_ready(self, api_client, ready_dataset):
        resp = api_client.post(
            f"/api/v1/qualitative/datasets/{ready_dataset.id}/analyses/"
        )
        assert resp.status_code == 202
        assert resp.json()["status"] == "queued"

    def test_conflict_when_not_ready(self, api_client, make_dataset):
        ds = make_dataset(status="building")
        resp = api_client.post(f"/api/v1/qualitative/datasets/{ds.id}/analyses/")
        assert resp.status_code == 409


@pytest.mark.django_db
class TestIngestFromEvent:
    @patch("quality.services.dataset_service.run_build_in_background")
    def test_creates_pending_dataset_without_auto_build(self, mock_build):
        payload = {
            "for_qualitative": True,
            "collection_id": 42,
            "user_id": 1,
            "workspace_id": 1,
            "repository_full_name": "owner/repo",
            "platform": "github",
            "qualitative_data_filename": "owner_repo.qualitative.json",
        }
        dataset = DatasetService.ingest_from_event(payload)
        assert dataset is not None
        assert dataset.status == "pending"  # collected, awaiting manual prepare
        assert QualitativeDataset.objects.filter(collection_id=42).exists()
        mock_build.assert_not_called()

    @patch("quality.services.dataset_service.run_build_in_background")
    def test_ignores_non_qualitative_event(self, mock_build):
        assert DatasetService.ingest_from_event({"for_qualitative": False}) is None
        mock_build.assert_not_called()
