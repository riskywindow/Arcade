from __future__ import annotations

from dataclasses import dataclass

from atlas_core.domain import (
    RunResumedPayload,
    RunCompletedPayload,
    RunEvent,
    RunEventType,
    RunReadyPayload,
    RunStartedPayload,
    RunStatus,
    RunStopRequestedPayload,
    RunWaitingApprovalPayload,
)

TERMINAL_RUN_STATUSES = frozenset(
    {
        RunStatus.SUCCEEDED,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    }
)

ALLOWED_RUN_STATUS_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.PENDING: frozenset({RunStatus.READY, RunStatus.FAILED, RunStatus.CANCELLED}),
    RunStatus.READY: frozenset({RunStatus.RUNNING, RunStatus.FAILED, RunStatus.CANCELLED}),
    RunStatus.RUNNING: frozenset(
        {
            RunStatus.WAITING_APPROVAL,
            RunStatus.SUCCEEDED,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
        }
    ),
    RunStatus.WAITING_APPROVAL: frozenset(
        {
            RunStatus.RUNNING,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
        }
    ),
    RunStatus.SUCCEEDED: frozenset(),
    RunStatus.FAILED: frozenset(),
    RunStatus.CANCELLED: frozenset(),
}


class RunStateMachineError(Exception):
    """Base error for run lifecycle validation."""


class InvalidRunTransitionError(RunStateMachineError):
    """Raised when a Run transition is not allowed."""


class InvalidRunEventTransitionError(RunStateMachineError):
    """Raised when a RunEvent implies an illegal Run transition."""


@dataclass(frozen=True)
class RunTransition:
    from_status: RunStatus
    to_status: RunStatus
    reason: str


def allowed_transitions(status: RunStatus) -> frozenset[RunStatus]:
    return ALLOWED_RUN_STATUS_TRANSITIONS[status]


def validate_run_transition(from_status: RunStatus, to_status: RunStatus) -> RunTransition:
    if from_status == to_status:
        return RunTransition(from_status=from_status, to_status=to_status, reason="no-op")

    allowed = allowed_transitions(from_status)
    if to_status not in allowed:
        allowed_values = ", ".join(sorted(status.value for status in allowed)) or "none"
        raise InvalidRunTransitionError(
            f"invalid run transition from {from_status.value} to {to_status.value}; "
            f"allowed targets: {allowed_values}"
        )
    return RunTransition(from_status=from_status, to_status=to_status, reason="allowed")


def transition_status_for_event(event: RunEvent) -> RunStatus | None:
    payload = event.payload
    if event.event_type == RunEventType.RUN_READY:
        ready_payload = payload
        assert isinstance(ready_payload, RunReadyPayload)
        return ready_payload.status
    if event.event_type == RunEventType.RUN_STARTED:
        started_payload = payload
        assert isinstance(started_payload, RunStartedPayload)
        return started_payload.status
    if event.event_type == RunEventType.RUN_STOP_REQUESTED:
        assert isinstance(payload, RunStopRequestedPayload)
        return None
    if event.event_type == RunEventType.RUN_WAITING_APPROVAL:
        waiting_payload = payload
        assert isinstance(waiting_payload, RunWaitingApprovalPayload)
        return waiting_payload.status
    if event.event_type == RunEventType.RUN_RESUMED:
        resumed_payload = payload
        assert isinstance(resumed_payload, RunResumedPayload)
        return resumed_payload.status
    if event.event_type == RunEventType.RUN_COMPLETED:
        completed_payload = payload
        assert isinstance(completed_payload, RunCompletedPayload)
        return completed_payload.final_status
    return None


def validate_event_transition(current_status: RunStatus, event: RunEvent) -> RunTransition | None:
    target_status = transition_status_for_event(event)
    if target_status is None:
        return None
    try:
        return validate_run_transition(current_status, target_status)
    except InvalidRunTransitionError as exc:
        raise InvalidRunEventTransitionError(
            f"event {event.event_type.value} cannot move run from "
            f"{current_status.value} to {target_status.value}"
        ) from exc
