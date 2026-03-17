from __future__ import annotations

import pytest

from atlas_env_helpdesk import HelpdeskService, InboxThreadNotFoundError


def test_list_inbox_threads_returns_seeded_threads() -> None:
    service = HelpdeskService.seeded("seed-phase3-demo")

    threads = service.list_inbox_threads()

    assert threads.seed == "seed-phase3-demo"
    assert len(threads.threads) == 5
    assert threads.threads[0].message_count >= 1


def test_get_inbox_thread_returns_thread_detail() -> None:
    service = HelpdeskService.seeded("seed-phase3-demo")
    thread_id = next(
        thread.thread_id
        for thread in service.list_inbox_threads().threads
        if thread.subject == "Travel access issue details"
    )

    thread = service.get_inbox_thread(thread_id)

    assert thread.subject == "Travel access issue details"
    assert thread.messages[0].sender == "tessa.nguyen@northstar-health.example"


def test_inbox_threads_are_stable_after_ticket_mutation_and_reset() -> None:
    service = HelpdeskService.seeded("seed-phase3-demo")
    baseline = service.list_inbox_threads()

    ticket_id = service.list_ticket_queue().tickets[0].ticket_id
    service.add_note(ticket_id, author="samir.holt", body="Checked inbox context.")

    assert service.list_inbox_threads() == baseline

    service.reset()

    assert service.list_inbox_threads() == baseline


def test_get_inbox_thread_raises_for_unknown_id() -> None:
    service = HelpdeskService.seeded("seed-phase3-demo")

    with pytest.raises(InboxThreadNotFoundError):
        service.get_inbox_thread("thread_missing")
