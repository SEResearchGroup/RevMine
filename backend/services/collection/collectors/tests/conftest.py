"""
Fixtures for the collectors.tests package.

These replace the root-level conftest.py for tests that live within
the :mod:`collectors.tests` package.  The root ``conftest.py`` at the
``collection/`` service level also remains active, so fixtures defined
there (``api_client``, ``create_collection``, etc.) are still available.
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from rest_framework.test import APIClient


# ---------------------------------------------------------------------------
# MinIO mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_minio(monkeypatch):
    """Completely replace MinIOClient with a lightweight in-memory stub."""
    storage: dict = {}

    class _FakeMinIO:
        # Bucket housekeeping — no-ops
        def __init__(self):
            pass

        def _ensure_bucket_exists(self):
            pass

        def generate_filename(self, repo, coll_id, ext):
            return f"{repo}_{coll_id}.{ext}"

        def save_json(self, data, filename):
            storage[filename] = data
            return True

        def get_json(self, filename):
            return storage.get(filename)

        def get_json_bytes(self, filename):
            import json
            data = storage.get(filename)
            return json.dumps(data).encode() if data else None

        def save_csv(self, content, filename):
            storage[filename] = content
            return True

        def get_csv(self, filename):
            return storage.get(filename)

        def get_csv_bytes(self, filename):
            data = storage.get(filename)
            return data.encode() if isinstance(data, str) else data

        def file_exists(self, filename):
            return filename in storage

        def delete_file(self, filename):
            storage.pop(filename, None)
            return True

        def get_object_stream(self, filename):
            return None

        def save_stream(self, *args, **kwargs):
            return True

    monkeypatch.setattr(
        "collectors.infrastructure.storage.minio_client.MinIOClient",
        _FakeMinIO,
    )
    # Also patch the compat shim so imports from the old path still work
    monkeypatch.setattr(
        "collectors.minio_client.MinIOClient",
        _FakeMinIO,
    )
    return _FakeMinIO, storage


# ---------------------------------------------------------------------------
# Kafka mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_kafka(monkeypatch):
    """Stub out KafkaClient.publish so tests never touch a real broker."""
    published: list = []

    def _fake_publish(topic, payload):
        published.append({"topic": topic, "payload": payload})

    monkeypatch.setattr("kafka_utils.client.KafkaClient.publish", staticmethod(_fake_publish))
    return published


# ---------------------------------------------------------------------------
# Authenticated API client
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_client():
    client = APIClient()
    client.credentials(HTTP_X_USER_ID="1")
    return client
