from __future__ import annotations

from atlas_core import ToolRequest, ToolResultOutcome
from atlas_env_helpdesk import HelpdeskService
from atlas_worker import HelpdeskTicketToolExecutor, build_phase4_tool_registry_with_browser


def test_helpdesk_ticket_tool_executor_lists_and_updates_tickets() -> None:
    service = HelpdeskService.seeded("seed-phase3-demo")
    executor = HelpdeskTicketToolExecutor(service)
    ticket_id = service.list_ticket_queue().tickets[0].ticket_id

    list_result = executor.execute(
        ToolRequest(
            request_id="toolreq_ticket_001",
            tool_name="helpdesk_ticket",
            arguments={"action": "list_tickets", "query": "travel"},
        )
    )
    assert list_result.outcome == ToolResultOutcome.SUCCESS
    assert list_result.result is not None
    assert list_result.result["matched_ticket_ids"]

    status_result = executor.execute(
        ToolRequest(
            request_id="toolreq_ticket_002",
            tool_name="helpdesk_ticket",
            arguments={
                "action": "update_status",
                "ticket_id": ticket_id,
                "status": "in_progress",
            },
        )
    )
    assert status_result.outcome == ToolResultOutcome.SUCCESS
    assert status_result.result is not None
    assert status_result.result["ticket"]["status"] == "in_progress"


def test_helpdesk_ticket_tool_executor_rejects_bad_requests() -> None:
    executor = HelpdeskTicketToolExecutor(HelpdeskService.seeded("seed-phase3-demo"))

    result = executor.execute(
        ToolRequest(
            request_id="toolreq_ticket_bad",
            tool_name="helpdesk_ticket",
            arguments={"action": "add_note", "ticket_id": "ticket_missing"},
        )
    )

    assert result.outcome == ToolResultOutcome.INVALID_REQUEST


def test_phase4_registry_can_invoke_helpdesk_ticket_tool() -> None:
    registry = build_phase4_tool_registry_with_browser(
        helpdesk_ticket_executor=HelpdeskTicketToolExecutor(
            HelpdeskService.seeded("seed-phase3-demo")
        )
    )

    result = registry.execute(
        ToolRequest(
            request_id="toolreq_ticket_003",
            tool_name="helpdesk_ticket",
            arguments={"action": "list_tickets"},
        )
    )

    assert result.outcome == ToolResultOutcome.SUCCESS
    assert result.metadata["action"] == "list_tickets"
