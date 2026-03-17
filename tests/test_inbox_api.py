from __future__ import annotations

from fastapi.testclient import TestClient

from atlas_api.app import create_app
from atlas_api.config import ApiConfig
from atlas_core.config import InfrastructureConfig, ServiceConfig


def _client() -> TestClient:
    config = ApiConfig(
        service=ServiceConfig(
            service_name="atlas-api",
            environment="test",
            host="127.0.0.1",
            port=8000,
            log_level="INFO",
            reload=False,
        ),
        infrastructure=InfrastructureConfig.from_env(),
    )
    return TestClient(create_app(config))


def test_inbox_api_lists_seeded_threads() -> None:
    client = _client()

    response = client.get("/environments/helpdesk/inbox/threads")

    assert response.status_code == 200
    payload = response.json()
    assert payload["seed"] == "seed-phase3-demo"
    assert len(payload["threads"]) == 5


def test_inbox_api_gets_thread_detail() -> None:
    client = _client()
    list_response = client.get("/environments/helpdesk/inbox/threads")
    thread_id = list_response.json()["threads"][0]["threadId"]

    response = client.get(f"/environments/helpdesk/inbox/threads/{thread_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["thread"]["threadId"] == thread_id
    assert payload["thread"]["messages"]


def test_inbox_api_rejects_unknown_thread() -> None:
    client = _client()

    response = client.get("/environments/helpdesk/inbox/threads/thread_missing")

    assert response.status_code == 404
