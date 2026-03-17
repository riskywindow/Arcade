from __future__ import annotations

import pytest

from atlas_env_helpdesk import (
    HelpdeskService,
    HelpdeskTicketNotFoundError,
    InvalidTicketTransitionError,
    NoteKind,
    TicketStatus,
)


def test_helpdesk_service_lists_seeded_ticket_queue() -> None:
    service = HelpdeskService.seeded("seed-phase3-demo")

    queue = service.list_ticket_queue()

    assert queue.seed == "seed-phase3-demo"
    assert len(queue.tickets) == 9
    assert queue.tickets[0].ticket_id.startswith("ticket_")


def test_helpdesk_service_returns_ticket_detail_with_linked_context() -> None:
    service = HelpdeskService.seeded("seed-phase3-demo")
    ticket_id = service.list_ticket_queue().tickets[0].ticket_id

    detail = service.get_ticket_detail(ticket_id)

    assert detail.ticket.ticket_id == ticket_id
    assert detail.requester.email.endswith("@northstar-health.example")
    assert detail.related_employee is not None
    assert detail.related_device is not None


def test_helpdesk_service_supports_assignment_status_and_notes() -> None:
    service = HelpdeskService.seeded("seed-phase3-demo")
    ticket_id = service.list_ticket_queue().tickets[0].ticket_id

    assigned = service.assign_ticket(ticket_id, assigned_to="samir.holt")
    in_progress = service.transition_ticket_status(ticket_id, status=TicketStatus.IN_PROGRESS)
    noted = service.add_note(
        ticket_id,
        author="samir.holt",
        body="Reviewed the account context and started troubleshooting.",
        kind=NoteKind.INTERNAL,
    )

    assert assigned.assigned_to == "samir.holt"
    assert in_progress.status == TicketStatus.IN_PROGRESS
    assert noted.notes[-1].author == "samir.holt"
    assert noted.notes[-1].body.startswith("Reviewed")


def test_helpdesk_service_reset_restores_seeded_state() -> None:
    service = HelpdeskService.seeded("seed-phase3-demo")
    ticket = service.list_ticket_queue().tickets[0]

    service.assign_ticket(ticket.ticket_id, assigned_to="samir.holt")
    service.transition_ticket_status(ticket.ticket_id, status=TicketStatus.IN_PROGRESS)
    service.add_note(
        ticket.ticket_id,
        author="samir.holt",
        body="Working the ticket.",
        kind=NoteKind.INTERNAL,
    )

    reset_queue = service.reset()
    reset_ticket = next(item for item in reset_queue.tickets if item.ticket_id == ticket.ticket_id)

    assert reset_ticket.assigned_to is None
    assert reset_ticket.status == ticket.status
    assert reset_ticket.notes == ()


def test_helpdesk_service_rejects_invalid_transitions_and_missing_tickets() -> None:
    service = HelpdeskService.seeded("seed-phase3-demo")
    ticket_id = service.list_ticket_queue().tickets[0].ticket_id
    service.transition_ticket_status(ticket_id, status=TicketStatus.RESOLVED)

    with pytest.raises(InvalidTicketTransitionError):
        service.transition_ticket_status(ticket_id, status=TicketStatus.PENDING_USER)

    with pytest.raises(HelpdeskTicketNotFoundError):
        service.get_ticket_detail("ticket_missing")
