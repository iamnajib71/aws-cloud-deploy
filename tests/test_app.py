import json
from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient

from app import main


@pytest.fixture
def client(monkeypatch):
    storage = Mock()
    storage.scan.return_value = {"Items": []}
    monkeypatch.setattr(main, "table", lambda: storage)
    with TestClient(main.app) as test_client:
        yield test_client, storage


def test_health_checks_storage(client):
    api, storage = client
    assert api.get("/health").json() == {"status": "ok"}
    storage.get_item.assert_called_once_with(Key={"id": "readiness-probe"})


def test_broken_release_readiness(client, monkeypatch):
    api, _ = client
    monkeypatch.setenv("RELEASE_HEALTH", "broken")
    assert api.get("/health").status_code == 503


def test_storage_failure_returns_503(client):
    api, storage = client
    storage.get_item.side_effect = ClientError(
        {"Error": {"Code": "AccessDeniedException"}}, "GetItem"
    )
    assert api.get("/health").status_code == 503


def test_create_and_list(client):
    api, storage = client
    response = api.post("/items", json={"name": "demo"})
    assert response.status_code == 201
    item = response.json()
    storage.put_item.assert_called_once_with(Item=item)
    storage.scan.return_value = {"Items": [item], "LastEvaluatedKey": {"id": item["id"]}}
    assert api.get("/items").json() == {"items": [item], "truncated": True}


def test_input_bounds(client):
    api, storage = client
    for name in ["", "x" * 81]:
        assert api.post("/items", json={"name": name}).status_code == 422
    storage.put_item.assert_not_called()


def test_metrics_and_structured_logs(client, caplog):
    api, _ = client
    api.get("/health")
    response = api.get("/metrics")
    assert "api_requests_total" in response.text
    records = [json.loads(r.message) for r in caplog.records if r.name == "items"]
    assert records[-1]["route"] == "/metrics"
    assert "duration_ms" in records[-1]


def test_http_api_v2_event_reaches_lambda_handler(monkeypatch):
    monkeypatch.setattr(main, "table", lambda: Mock())
    event = {
        "version": "2.0",
        "routeKey": "GET /health",
        "rawPath": "/health",
        "rawQueryString": "",
        "headers": {"host": "example.invalid", "x-forwarded-proto": "https"},
        "requestContext": {
            "stage": "$default",
            "http": {"method": "GET", "path": "/health", "sourceIp": "127.0.0.1"},
        },
        "isBase64Encoded": False,
    }
    response = main.handler(event, Mock())
    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"status": "ok"}
