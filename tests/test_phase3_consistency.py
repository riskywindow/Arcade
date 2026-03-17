from __future__ import annotations

from atlas_env_helpdesk import HelpdeskService, NoteKind, TicketStatus


def _public_snapshot(service: HelpdeskService) -> dict[str, object]:
    queue = service.list_ticket_queue()
    directory = service.list_employees()
    wiki = service.list_wiki_documents()
    inbox = service.list_inbox_threads()

    first_ticket = queue.tickets[0]
    first_employee = directory.employees[0]
    first_thread = inbox.threads[0]
    first_document = wiki.documents[0]

    return {
        "queue": queue.model_dump(mode="json"),
        "directory": directory.model_dump(mode="json"),
        "wiki": wiki.model_dump(mode="json"),
        "inbox": inbox.model_dump(mode="json"),
        "ticket_detail": service.get_ticket_detail(first_ticket.ticket_id).model_dump(mode="json"),
        "employee_detail": service.get_employee_detail(first_employee.employee_id).model_dump(
            mode="json"
        ),
        "wiki_document": service.get_wiki_document(first_document.slug).model_dump(mode="json"),
        "inbox_thread": service.get_inbox_thread(first_thread.thread_id).model_dump(mode="json"),
    }


def test_repeated_reset_cycles_restore_identical_public_state() -> None:
    service = HelpdeskService.seeded("seed-phase3-demo")
    baseline = _public_snapshot(service)
    first_ticket = service.list_ticket_queue().tickets[0]

    for cycle in range(3):
        service.assign_ticket(first_ticket.ticket_id, assigned_to=f"samir.holt.{cycle}")
        service.transition_ticket_status(first_ticket.ticket_id, status=TicketStatus.IN_PROGRESS)
        service.add_note(
            first_ticket.ticket_id,
            author="samir.holt",
            body=f"Cycle {cycle} mutation for reset verification.",
            kind=NoteKind.INTERNAL,
        )

        employee_detail = service.get_employee_detail(first_ticket.requester_employee_id)
        service.update_account_access(
            employee_detail.employee.employee_id,
            account_locked=False,
            mfa_enrolled=True,
            groups=(*employee_detail.account_access.groups, f"temp-group-{cycle}"),
        )
        related_device_id = first_ticket.related_device_id
        assert related_device_id is not None
        service.update_device(
            related_device_id,
            health_state=f"repairing-{cycle}",
            compromised=bool(cycle % 2),
        )

        assert _public_snapshot(service) != baseline
        service.reset()
        assert _public_snapshot(service) == baseline


def test_seeded_services_are_isolated_from_each_other() -> None:
    primary = HelpdeskService.seeded("seed-phase3-demo")
    secondary = HelpdeskService.seeded("seed-phase3-demo")

    baseline = _public_snapshot(primary)
    ticket = primary.list_ticket_queue().tickets[0]
    primary.assign_ticket(ticket.ticket_id, assigned_to="samir.holt")
    primary.transition_ticket_status(ticket.ticket_id, status=TicketStatus.IN_PROGRESS)
    primary.add_note(
        ticket.ticket_id,
        author="samir.holt",
        body="Primary service only mutation.",
        kind=NoteKind.INTERNAL,
    )

    assert _public_snapshot(primary) != baseline
    assert _public_snapshot(secondary) == baseline


def test_hidden_scenario_state_resolution_is_deterministic_per_seed() -> None:
    from atlas_env_helpdesk import get_hidden_scenario_state

    first = get_hidden_scenario_state("travel-lockout-recovery", seed="seed-phase3-demo")
    second = get_hidden_scenario_state("travel-lockout-recovery", seed="seed-phase3-demo")
    alternate = get_hidden_scenario_state("travel-lockout-recovery", seed="seed-phase3-alt")

    assert first == second
    assert first.target_ticket_id != alternate.target_ticket_id
    assert first.owner == alternate.owner
    assert first.required_doc_slugs == alternate.required_doc_slugs


def test_hidden_state_resolves_for_every_frozen_scenario() -> None:
    from atlas_env_helpdesk import get_hidden_scenario_state, list_scenarios

    scenarios = list_scenarios()
    resolved_ids = {get_hidden_scenario_state(scenario.scenario_id).scenario_id for scenario in scenarios}
    assert resolved_ids == {scenario.scenario_id for scenario in scenarios}
