from __future__ import annotations

from pathlib import Path

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


def _collect_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            keys.add(str(key))
            keys.update(_collect_keys(nested))
    elif isinstance(value, list):
        for item in value:
            keys.update(_collect_keys(item))
    return keys


def test_public_api_payloads_use_phase_three_transport_keys_and_hide_private_fields() -> None:
    client = _client()
    ticket_id = client.get("/environments/helpdesk/tickets").json()["tickets"][0]["ticketId"]
    employee_id = client.get("/environments/helpdesk/directory/employees").json()["employees"][0][
        "employeeId"
    ]
    wiki_slug = client.get("/environments/helpdesk/wiki/documents").json()["documents"][0]["slug"]
    thread_id = client.get("/environments/helpdesk/inbox/threads").json()["threads"][0]["threadId"]

    payload = {
        "tickets": client.get("/environments/helpdesk/tickets").json(),
        "ticketDetail": client.get(f"/environments/helpdesk/tickets/{ticket_id}").json(),
        "directory": client.get("/environments/helpdesk/directory/employees").json(),
        "employeeDetail": client.get(
            f"/environments/helpdesk/directory/employees/{employee_id}"
        ).json(),
        "wiki": client.get("/environments/helpdesk/wiki/documents").json(),
        "wikiDetail": client.get(f"/environments/helpdesk/wiki/documents/{wiki_slug}").json(),
        "wikiSearch": client.get("/environments/helpdesk/wiki/search", params={"q": "travel"}).json(),
        "inbox": client.get("/environments/helpdesk/inbox/threads").json(),
        "inboxDetail": client.get(f"/environments/helpdesk/inbox/threads/{thread_id}").json(),
    }

    keys = _collect_keys(payload)

    assert "ticketId" in keys
    assert "requesterEmployeeId" in keys
    assert "accountAccess" in keys
    assert "relatedTickets" in keys
    assert "participantEmails" in keys
    assert "messageCount" in keys
    assert "matchedTerms" in keys

    assert "ticket_id" not in keys
    assert "requester_employee_id" not in keys
    assert "participant_emails" not in keys
    assert "message_count" not in keys
    assert "hidden_truth" not in keys
    assert "hidden_state_refs" not in keys
    assert "grader_hooks" not in keys
    assert "root_cause" not in keys


def test_shared_types_export_phase_three_public_contracts() -> None:
    source = Path("packages/shared-types/src/index.ts").read_text(encoding="utf-8")

    required_exports = (
        "export type HelpdeskTicketQueueResponse",
        "export type DirectoryEmployeeDetailResponse",
        "export type WikiDocumentListResponse",
        "export type InboxThreadListResponse",
        "export type InboxThreadResponse",
    )

    for export_name in required_exports:
        assert export_name in source
