from __future__ import annotations

from atlas_env_helpdesk import (
    HelpdeskService,
    HelpdeskTicketToolAction,
    HelpdeskTicketToolAdapter,
    HelpdeskTicketToolRequest,
    NoteKind,
    TicketStatus,
)


def test_ticket_tool_adapter_lists_and_filters_seeded_tickets() -> None:
    service = HelpdeskService.seeded("seed-phase3-demo")
    adapter = HelpdeskTicketToolAdapter(service)

    result = adapter.execute(
        HelpdeskTicketToolRequest(
            action=HelpdeskTicketToolAction.LIST_TICKETS,
            query="travel",
        )
    )

    assert result.queue is not None
    assert result.matched_ticket_ids
    assert all("travel" in ticket.title.lower() or "travel" in ticket.summary.lower() for ticket in result.queue.tickets)


def test_ticket_tool_adapter_gets_ticket_and_applies_note_and_status_change() -> None:
    service = HelpdeskService.seeded("seed-phase3-demo")
    adapter = HelpdeskTicketToolAdapter(service)
    ticket_id = service.list_ticket_queue().tickets[0].ticket_id

    detail_result = adapter.execute(
        HelpdeskTicketToolRequest(
            action=HelpdeskTicketToolAction.GET_TICKET,
            ticket_id=ticket_id,
        )
    )
    assert detail_result.detail is not None
    assert detail_result.detail.ticket.ticket_id == ticket_id

    note_result = adapter.execute(
        HelpdeskTicketToolRequest(
            action=HelpdeskTicketToolAction.ADD_NOTE,
            ticket_id=ticket_id,
            author="agent.phase4",
            note_body="Reviewed the seeded ticket context.",
            note_kind=NoteKind.INTERNAL,
        )
    )
    assert note_result.ticket is not None
    assert note_result.change_set is not None
    assert note_result.change_set.note_count_after == 1

    status_result = adapter.execute(
        HelpdeskTicketToolRequest(
            action=HelpdeskTicketToolAction.UPDATE_STATUS,
            ticket_id=ticket_id,
            status=TicketStatus.IN_PROGRESS,
        )
    )
    assert status_result.ticket is not None
    assert status_result.ticket.status == TicketStatus.IN_PROGRESS
    assert status_result.change_set is not None
    assert status_result.change_set.previous_status == "open"
    assert status_result.change_set.new_status == "in_progress"


def test_ticket_tool_adapter_resolves_public_scenario_ticket_identifier() -> None:
    service = HelpdeskService.seeded("seed-phase3-demo")
    adapter = HelpdeskTicketToolAdapter(service)

    detail_result = adapter.execute(
        HelpdeskTicketToolRequest(
            action=HelpdeskTicketToolAction.GET_TICKET,
            ticket_id="ticket_mfa_reenrollment_device_loss",
        )
    )

    assert detail_result.detail is not None
    assert detail_result.detail.ticket.title == "Cannot complete MFA after losing phone"


def test_ticket_tool_adapter_changes_reset_with_service_reset() -> None:
    service = HelpdeskService.seeded("seed-phase3-demo")
    adapter = HelpdeskTicketToolAdapter(service)
    ticket_id = service.list_ticket_queue().tickets[0].ticket_id

    adapter.execute(
        HelpdeskTicketToolRequest(
            action=HelpdeskTicketToolAction.ADD_NOTE,
            ticket_id=ticket_id,
            author="agent.phase4",
            note_body="Temporary note before reset.",
        )
    )
    adapter.execute(
        HelpdeskTicketToolRequest(
            action=HelpdeskTicketToolAction.UPDATE_STATUS,
            ticket_id=ticket_id,
            status=TicketStatus.IN_PROGRESS,
        )
    )

    reset_queue = service.reset()
    reset_ticket = next(ticket for ticket in reset_queue.tickets if ticket.ticket_id == ticket_id)

    assert reset_ticket.status == TicketStatus.OPEN
    assert reset_ticket.notes == ()
