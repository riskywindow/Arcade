from __future__ import annotations

from datetime import UTC, datetime

import pytest

from atlas_core import (
    ActorType,
    InvalidRunEventTransitionError,
    InvalidRunTransitionError,
    Run,
    RunCompletedPayload,
    RunCreatedPayload,
    RunEvent,
    RunEventSource,
    RunEventType,
    RunReadyPayload,
    RunStepCreatedPayload,
    RunStartedPayload,
    RunStatus,
    ScenarioRef,
    TaskRef,
    EnvironmentRef,
    allowed_transitions,
    transition_status_for_event,
    validate_event_transition,
    validate_run_transition,
)


def _timestamp() -> datetime:
    return datetime(2026, 3, 15, 12, 0, tzinfo=UTC)


def _run() -> Run:
    return Run(
        run_id="run_123",
        environment=EnvironmentRef(
            environment_id="env_helpdesk",
            environment_name="Northstar Helpdesk",
            environment_version="v1",
        ),
        scenario=ScenarioRef(
            scenario_id="scn_123",
            environment_id="env_helpdesk",
            scenario_name="travel-lockout",
            scenario_seed="seed-123",
        ),
        task=TaskRef(
            task_id="task_123",
            scenario_id="scn_123",
            task_kind="access_restoration",
            task_title="Restore employee access after travel lockout",
        ),
        status=RunStatus.PENDING,
        created_at=_timestamp(),
        updated_at=_timestamp(),
    )


def _event(event_type: RunEventType) -> RunEvent:
    run = _run()
    payload: (
        RunCreatedPayload
        | RunReadyPayload
        | RunStartedPayload
        | RunStepCreatedPayload
        | RunCompletedPayload
    )
    if event_type == RunEventType.RUN_CREATED:
        payload = RunCreatedPayload(
            event_type=RunEventType.RUN_CREATED,
            run=run,
        )
    elif event_type == RunEventType.RUN_READY:
        payload = RunReadyPayload(
            event_type=RunEventType.RUN_READY,
            run_id=run.run_id,
            status=RunStatus.READY,
        )
    elif event_type == RunEventType.RUN_STARTED:
        payload = RunStartedPayload(
            event_type=RunEventType.RUN_STARTED,
            run_id=run.run_id,
            status=RunStatus.RUNNING,
            started_at=_timestamp(),
        )
    else:
        payload = RunCompletedPayload(
            event_type=RunEventType.RUN_COMPLETED,
            run_id=run.run_id,
            final_status=RunStatus.SUCCEEDED,
            completed_at=_timestamp(),
        )
    return RunEvent(
        event_id=f"evt_{event_type.value}",
        run_id=run.run_id,
        sequence=0,
        occurred_at=_timestamp(),
        source=RunEventSource.SYSTEM,
        actor_type=ActorType.SYSTEM,
        event_type=event_type,
        payload=payload,
    )


def test_allowed_transitions_are_explicit() -> None:
    assert allowed_transitions(RunStatus.PENDING) == frozenset(
        {RunStatus.READY, RunStatus.FAILED, RunStatus.CANCELLED}
    )
    assert allowed_transitions(RunStatus.RUNNING) == frozenset(
        {
            RunStatus.WAITING_APPROVAL,
            RunStatus.SUCCEEDED,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
        }
    )


def test_validate_run_transition_accepts_valid_path() -> None:
    transition = validate_run_transition(RunStatus.READY, RunStatus.RUNNING)

    assert transition.from_status == RunStatus.READY
    assert transition.to_status == RunStatus.RUNNING


def test_validate_run_transition_rejects_invalid_path() -> None:
    with pytest.raises(InvalidRunTransitionError):
        validate_run_transition(RunStatus.PENDING, RunStatus.RUNNING)


def test_transition_status_for_event_maps_lifecycle_events() -> None:
    assert transition_status_for_event(_event(RunEventType.RUN_CREATED)) is None
    assert transition_status_for_event(_event(RunEventType.RUN_READY)) == RunStatus.READY
    assert transition_status_for_event(_event(RunEventType.RUN_STARTED)) == RunStatus.RUNNING
    assert transition_status_for_event(_event(RunEventType.RUN_COMPLETED)) == RunStatus.SUCCEEDED


def test_validate_event_transition_rejects_invalid_lifecycle_event() -> None:
    with pytest.raises(InvalidRunEventTransitionError):
        validate_event_transition(RunStatus.PENDING, _event(RunEventType.RUN_STARTED))
