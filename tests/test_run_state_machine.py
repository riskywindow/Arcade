from __future__ import annotations

from datetime import UTC, datetime

import pytest

from atlas_core import (
    ActorType,
    ApprovalRequestedPayload,
    InvalidRunEventTransitionError,
    InvalidRunTransitionError,
    Run,
    RunCompletedPayload,
    RunCreatedPayload,
    RunEvent,
    RunEventSource,
    RunEventType,
    RunReadyPayload,
    RunResumedPayload,
    RunStopRequestedPayload,
    RunStepCreatedPayload,
    RunStartedPayload,
    RunStatus,
    RunWaitingApprovalPayload,
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
        | RunStopRequestedPayload
        | RunWaitingApprovalPayload
        | RunResumedPayload
        | ApprovalRequestedPayload
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
    elif event_type == RunEventType.RUN_STOP_REQUESTED:
        payload = RunStopRequestedPayload(
            event_type=RunEventType.RUN_STOP_REQUESTED,
            run_id=run.run_id,
            stop_request_id="stop_123",
            operator_id="operator_123",
            requested_at=_timestamp(),
            reason="operator requested stop",
        )
    elif event_type == RunEventType.RUN_WAITING_APPROVAL:
        payload = RunWaitingApprovalPayload(
            event_type=RunEventType.RUN_WAITING_APPROVAL,
            run_id=run.run_id,
            status=RunStatus.WAITING_APPROVAL,
            approval_request_id="approval_123",
            waiting_at=_timestamp(),
        )
    elif event_type == RunEventType.RUN_RESUMED:
        payload = RunResumedPayload(
            event_type=RunEventType.RUN_RESUMED,
            run_id=run.run_id,
            status=RunStatus.RUNNING,
            approval_request_id="approval_123",
            resumed_at=_timestamp(),
        )
    elif event_type == RunEventType.APPROVAL_REQUESTED:
        payload = ApprovalRequestedPayload(
            event_type=RunEventType.APPROVAL_REQUESTED,
            run_id=run.run_id,
            approval_request={"approval_request_id": "approval_123"},
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
    assert transition_status_for_event(_event(RunEventType.RUN_STOP_REQUESTED)) is None
    assert transition_status_for_event(_event(RunEventType.RUN_WAITING_APPROVAL)) == RunStatus.WAITING_APPROVAL
    assert transition_status_for_event(_event(RunEventType.RUN_RESUMED)) == RunStatus.RUNNING
    assert transition_status_for_event(_event(RunEventType.APPROVAL_REQUESTED)) is None
    assert transition_status_for_event(_event(RunEventType.RUN_COMPLETED)) == RunStatus.SUCCEEDED


def test_validate_event_transition_rejects_invalid_lifecycle_event() -> None:
    with pytest.raises(InvalidRunEventTransitionError):
        validate_event_transition(RunStatus.PENDING, _event(RunEventType.RUN_STARTED))


def test_validate_run_transition_allows_waiting_approval_resume() -> None:
    transition = validate_run_transition(RunStatus.WAITING_APPROVAL, RunStatus.RUNNING)

    assert transition.from_status == RunStatus.WAITING_APPROVAL
    assert transition.to_status == RunStatus.RUNNING


def test_validate_run_transition_rejects_terminal_to_running() -> None:
    with pytest.raises(InvalidRunTransitionError):
        validate_run_transition(RunStatus.SUCCEEDED, RunStatus.RUNNING)


def test_validate_event_transition_allows_waiting_approval_and_resume_events() -> None:
    waiting_transition = validate_event_transition(RunStatus.RUNNING, _event(RunEventType.RUN_WAITING_APPROVAL))
    resumed_transition = validate_event_transition(
        RunStatus.WAITING_APPROVAL,
        _event(RunEventType.RUN_RESUMED),
    )

    assert waiting_transition is not None
    assert waiting_transition.to_status == RunStatus.WAITING_APPROVAL
    assert resumed_transition is not None
    assert resumed_transition.to_status == RunStatus.RUNNING
