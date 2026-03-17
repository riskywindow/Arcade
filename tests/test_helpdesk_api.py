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


def test_helpdesk_api_lists_gets_mutates_and_resets_tickets() -> None:
    client = _client()

    queue_response = client.get("/environments/helpdesk/tickets")
    assert queue_response.status_code == 200
    queue_payload = queue_response.json()
    assert queue_payload["seed"] == "seed-phase3-demo"
    assert len(queue_payload["tickets"]) == 9

    ticket_id = queue_payload["tickets"][0]["ticketId"]
    detail_response = client.get(f"/environments/helpdesk/tickets/{ticket_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["detail"]["ticket"]["ticketId"] == ticket_id
    assert detail_response.json()["detail"]["requester"]["email"].endswith(
        "@northstar-health.example"
    )

    assign_response = client.post(
        f"/environments/helpdesk/tickets/{ticket_id}/assignment",
        json={"assignedTo": "samir.holt"},
    )
    assert assign_response.status_code == 200
    assert assign_response.json()["ticket"]["assignedTo"] == "samir.holt"

    status_response = client.post(
        f"/environments/helpdesk/tickets/{ticket_id}/status",
        json={"status": "in_progress"},
    )
    assert status_response.status_code == 200
    assert status_response.json()["ticket"]["status"] == "in_progress"

    note_response = client.post(
        f"/environments/helpdesk/tickets/{ticket_id}/notes",
        json={
            "author": "samir.holt",
            "body": "Investigated the issue and added an internal note.",
            "kind": "internal",
        },
    )
    assert note_response.status_code == 200
    assert len(note_response.json()["ticket"]["notes"]) == 1

    reset_response = client.post("/environments/helpdesk/reset")
    assert reset_response.status_code == 200
    reset_ticket = next(
        item for item in reset_response.json()["tickets"] if item["ticketId"] == ticket_id
    )
    assert reset_ticket["assignedTo"] is None
    assert reset_ticket["notes"] == []


def test_helpdesk_api_rejects_invalid_status_transition() -> None:
    client = _client()
    queue_response = client.get("/environments/helpdesk/tickets")
    ticket_id = queue_response.json()["tickets"][0]["ticketId"]

    resolved_response = client.post(
        f"/environments/helpdesk/tickets/{ticket_id}/status",
        json={"status": "resolved"},
    )
    assert resolved_response.status_code == 200

    invalid_response = client.post(
        f"/environments/helpdesk/tickets/{ticket_id}/status",
        json={"status": "pending_user"},
    )
    assert invalid_response.status_code == 409


def test_helpdesk_api_rejects_unknown_ticket_and_unknown_status() -> None:
    client = _client()

    missing_response = client.get("/environments/helpdesk/tickets/ticket_missing")
    assert missing_response.status_code == 404

    queue_response = client.get("/environments/helpdesk/tickets")
    ticket_id = queue_response.json()["tickets"][0]["ticketId"]
    bad_status_response = client.post(
        f"/environments/helpdesk/tickets/{ticket_id}/status",
        json={"status": "unsupported"},
    )
    assert bad_status_response.status_code == 422
