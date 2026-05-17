import pytest
from fastapi.testclient import TestClient

from main import app, get_openrouter_service, get_parser_service


class FakeParserService:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error

    def parse_user_request(self, user_message: str, model: str | None = None):
        if self.error:
            raise self.error
        return self.result or {
            "intent": "collect",
            "branch": [],
            "platform": "github",
            "metrics": ["creation_date"],
            "basic_filters": {
                "date_range": None,
                "pr_status": ["open", "closed", "merged"],
            },
            "cleaning_filters": {
                "refined_date_range": None,
                "file_extensions": [],
                "authors": [],
                "keywords": {"fields": [], "terms": []},
            },
            "features": [],
        }


@pytest.fixture
def client():
    app.dependency_overrides[get_parser_service] = lambda: FakeParserService()
    app.dependency_overrides[get_openrouter_service] = lambda: FakeParserService()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def fake_service_factory():
    def _factory(result=None, error=None):
        fake = FakeParserService(result=result, error=error)
        app.dependency_overrides[get_parser_service] = lambda: fake
        return fake

    return _factory
