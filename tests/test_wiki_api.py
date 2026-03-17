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


def test_list_wiki_documents_endpoint_returns_seeded_docs() -> None:
    client = _client()
    response = client.get("/environments/helpdesk/wiki/documents")

    assert response.status_code == 200
    payload = response.json()
    assert payload["seed"] == "seed-phase3-demo"
    assert len(payload["documents"]) == 8


def test_get_wiki_document_endpoint_returns_detail() -> None:
    client = _client()
    response = client.get("/environments/helpdesk/wiki/documents/travel-lockout-recovery")

    assert response.status_code == 200
    payload = response.json()
    assert payload["document"]["slug"] == "travel-lockout-recovery"
    assert payload["document"]["title"] == "Travel Lockout Recovery SOP"


def test_search_wiki_documents_endpoint_returns_ranked_matches() -> None:
    client = _client()
    response = client.get("/environments/helpdesk/wiki/search", params={"q": "travel mfa"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "travel mfa"
    assert payload["results"][0]["document"]["slug"] == "travel-lockout-recovery"


def test_get_wiki_document_endpoint_returns_not_found_for_unknown_doc() -> None:
    client = _client()
    response = client.get("/environments/helpdesk/wiki/documents/does-not-exist")

    assert response.status_code == 404
