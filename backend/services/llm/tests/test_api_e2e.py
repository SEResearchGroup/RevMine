from fastapi.testclient import TestClient

from main import app, get_parser_service


class SuccessParserService:
    def parse_user_request(self, user_message: str, model: str | None = None):
        return {
            "intent": "collect",
            "branch": [],
            "platform": "github",
            "metrics": ["creation_date", "merge_date"],
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
            "features": ["lead_time"],
        }


class BrokenParserService:
    def parse_user_request(self, user_message: str, model: str | None = None):
        raise ValueError("No JSON object found in model output.")


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_parse_endpoint_success():
    app.dependency_overrides[get_parser_service] = lambda: SuccessParserService()
    with TestClient(app) as client:
        response = client.post(
            "/parse",
            json={
                "user_message": "Collect merge requests and compute lead time",
                "model": "deepseek-r1",
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["model"] == "deepseek-r1"
    assert body["result"]["intent"] == "collect"
    assert "lead_time" in body["result"]["features"]


def test_parse_endpoint_invalid_model_json():
    app.dependency_overrides[get_parser_service] = lambda: BrokenParserService()
    with TestClient(app) as client:
        response = client.post(
            "/parse",
            json={
                "user_message": "Collect merge requests",
                "model": "deepseek-r1",
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 422
    body = response.json()
    assert body["detail"]["error"] == "invalid_model_json"
