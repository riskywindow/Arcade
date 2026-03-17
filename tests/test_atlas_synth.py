from __future__ import annotations

from atlas_synth import (
    CanonicalFixtureSession,
    FIXTURE_SLUG,
    AccountAccessState,
    BaseWorldSnapshot,
    CompanyRecord,
    SyntheticWorldSnapshot,
    TicketStatus,
    build_canonical_world,
    render_snapshot_diff,
    snapshot_document,
    summarize_world,
)


def test_build_canonical_world_is_deterministic_for_same_seed() -> None:
    first = build_canonical_world("seed-phase3-demo")
    second = build_canonical_world("seed-phase3-demo")

    assert first == second
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_build_canonical_world_changes_stable_ids_across_seeds() -> None:
    first = build_canonical_world("seed-phase3-demo")
    second = build_canonical_world("seed-phase3-alt")

    assert first.base_world.seed == "seed-phase3-demo"
    assert second.base_world.seed == "seed-phase3-alt"
    assert first.base_world.world_id != second.base_world.world_id
    assert first.base_world.company.company_id != second.base_world.company.company_id
    assert first.base_world.employees[0].employee_id != second.base_world.employees[0].employee_id

    assert first.base_world.company.name == second.base_world.company.name
    assert len(first.base_world.employees) == len(second.base_world.employees)
    assert len(first.base_world.tickets) == len(second.base_world.tickets)


def test_world_snapshot_contains_expected_phase_three_entities() -> None:
    snapshot = build_canonical_world("seed-phase3-demo")
    world = snapshot.base_world

    assert isinstance(snapshot, SyntheticWorldSnapshot)
    assert isinstance(world, BaseWorldSnapshot)
    assert isinstance(world.company, CompanyRecord)
    assert isinstance(world.account_access_states[0], AccountAccessState)
    assert snapshot.fixture_slug == FIXTURE_SLUG
    assert snapshot.scenario_overlays == ()
    assert world.company.name == "Northstar Health Systems"
    assert len(world.departments) == 6
    assert len(world.employees) == 10
    assert len(world.devices) == 10
    assert len(world.account_access_states) == 10
    assert len(world.tickets) == 9
    assert len(world.wiki_pages) == 8
    assert len(world.inbox_threads) == 5
    assert len(world.suspicious_events) == 2


def test_world_summary_is_small_and_diffable() -> None:
    summary = summarize_world(build_canonical_world("seed-phase3-demo"))

    assert summary.company_name == "Northstar Health Systems"
    assert summary.employee_count == 10
    assert summary.ticket_count == 9
    assert summary.wiki_page_count == 8
    assert summary.inbox_thread_count == 5
    assert summary.suspicious_event_count == 2


def test_world_snapshot_serializes_with_literal_schema_names() -> None:
    snapshot = build_canonical_world("seed-phase3-demo")
    payload = snapshot.model_dump(mode="json")

    assert payload["environment_slug"] == "northstar-helpdesk"
    assert "base_world" in payload
    assert "account_access_states" in payload["base_world"]
    assert "inbox_threads" in payload["base_world"]
    assert "scenario_overlays" in payload


def test_fixture_session_reset_restores_same_baseline_after_replacement() -> None:
    session = CanonicalFixtureSession.load("seed-phase3-demo")
    baseline = session.snapshot()

    mutated_ticket = baseline.base_world.tickets[0].model_copy(
        update={"status": TicketStatus.RESOLVED}
    )
    mutated_world = baseline.base_world.model_copy(
        update={"tickets": (mutated_ticket, *baseline.base_world.tickets[1:])}
    )
    mutated_snapshot = baseline.model_copy(update={"base_world": mutated_world})
    session.replace_current(mutated_snapshot)

    assert session.snapshot() != baseline
    assert "resolved" in session.diff_from_baseline()

    reset_snapshot = session.reset()

    assert reset_snapshot == baseline
    assert session.diff_from_baseline() == ""


def test_fixture_session_rehydrate_matches_seeded_builder_output() -> None:
    session = CanonicalFixtureSession.load("seed-phase3-demo")
    baseline = session.snapshot()

    rehydrated = session.rehydrate()

    assert rehydrated == baseline
    assert rehydrated == build_canonical_world("seed-phase3-demo")


def test_snapshot_document_and_render_diff_are_inspectable() -> None:
    before = build_canonical_world("seed-phase3-demo")
    session = CanonicalFixtureSession.load("seed-phase3-demo")
    altered_ticket = session.snapshot().base_world.tickets[0].model_copy(
        update={"summary": "Employee now reports total email and VPN outage during travel."}
    )
    altered_world = session.snapshot().base_world.model_copy(
        update={"tickets": (altered_ticket, *session.snapshot().base_world.tickets[1:])}
    )
    after = session.replace_current(session.snapshot().model_copy(update={"base_world": altered_world}))

    document = snapshot_document(before)
    diff = render_snapshot_diff(before, after)

    assert document["fixture_slug"] == FIXTURE_SLUG
    assert "total email and VPN outage" in diff
