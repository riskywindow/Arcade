from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from atlas_core import (
    ActorType,
    Artifact,
    ArtifactAttachedPayload,
    ArtifactKind,
    EnvironmentRef,
    GradeOutcome,
    GradeResult,
    PolicyDecision,
    PolicyDecisionOutcome,
    Run,
    RunCompletedPayload,
    RunCreatedPayload,
    RunEvent,
    RunEventSource,
    RunEventType,
    RunReadyPayload,
    RunStartedPayload,
    RunStatus,
    RunStep,
    RunStepCreatedPayload,
    RunStepStatus,
    ScenarioRef,
    TaskRef,
    ToolCall,
    ToolCallRecordedPayload,
    ToolCallStatus,
)


def _timestamp() -> datetime:
    return datetime(2026, 3, 15, 12, 0, tzinfo=UTC)


def _run() -> Run:
    timestamp = _timestamp()
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
        created_at=timestamp,
        updated_at=timestamp,
        current_step_index=0,
        active_agent_id="dummy-agent",
        grade_result=GradeResult(
            grade_id="grade_123",
            outcome=GradeOutcome.NOT_GRADED,
            score=None,
            summary="Grading has not run yet.",
        ),
    )


def test_run_model_round_trips_through_json() -> None:
    run = _run()

    payload = run.model_dump_json()
    parsed = Run.model_validate_json(payload)

    assert parsed == run


def test_run_event_serializes_with_explicit_payload_shape() -> None:
    run = _run()
    event = RunEvent(
        event_id="evt_001",
        run_id=run.run_id,
        sequence=0,
        occurred_at=_timestamp(),
        source=RunEventSource.WORKER,
        actor_type=ActorType.WORKER,
        correlation_id="corr_123",
        event_type=RunEventType.RUN_CREATED,
        payload=RunCreatedPayload(
            event_type=RunEventType.RUN_CREATED,
            run=run,
        ),
    )

    serialized = event.model_dump(mode="json")

    assert serialized["event_type"] == "run.created"
    assert serialized["schema_version"] == 1
    assert serialized["payload"]["schema_version"] == 1
    assert serialized["payload"]["event_type"] == "run.created"
    assert serialized["payload"]["run"]["run_id"] == "run_123"
    assert RunEvent.model_validate(serialized) == event


def test_run_event_supports_all_phase_two_payloads() -> None:
    timestamp = _timestamp()
    run = _run()
    step = RunStep(
        step_id="step_001",
        run_id=run.run_id,
        step_index=1,
        title="Inspect account state",
        status=RunStepStatus.IN_PROGRESS,
        started_at=timestamp,
    )
    tool_call = ToolCall(
        tool_call_id="tool_001",
        tool_name="identity_api",
        action="lookup_account",
        arguments={"employee_id": "emp_123"},
        status=ToolCallStatus.SUCCEEDED,
        result={"account_state": "locked"},
    )
    policy_decision = PolicyDecision(
        decision_id="policy_001",
        outcome=PolicyDecisionOutcome.ALLOW,
        action_type="identity.lookup",
        rationale="Read-only lookup is allowed.",
    )
    artifact = Artifact(
        artifact_id="artifact_001",
        run_id=run.run_id,
        step_id="step_001",
        kind=ArtifactKind.LOG,
        uri="minio://atlas-artifacts/run_123/log.json",
        content_type="application/json",
        created_at=timestamp,
        metadata={"source": "dummy-worker"},
    )
    payloads: list[
        RunReadyPayload
        | RunStartedPayload
        | RunStepCreatedPayload
        | ToolCallRecordedPayload
        | ArtifactAttachedPayload
        | RunCompletedPayload
    ] = [
        RunReadyPayload(
            event_type=RunEventType.RUN_READY,
            run_id=run.run_id,
            status=RunStatus.READY,
        ),
        RunStartedPayload(
            event_type=RunEventType.RUN_STARTED,
            run_id=run.run_id,
            status=RunStatus.RUNNING,
            started_at=timestamp,
        ),
        RunStepCreatedPayload(
            event_type=RunEventType.RUN_STEP_CREATED,
            run_id=run.run_id,
            step=step,
        ),
        ToolCallRecordedPayload(
            event_type=RunEventType.TOOL_CALL_RECORDED,
            run_id=run.run_id,
            step_id=step.step_id,
            tool_call=tool_call,
            policy_decision=policy_decision,
        ),
        ArtifactAttachedPayload(
            event_type=RunEventType.ARTIFACT_ATTACHED,
            run_id=run.run_id,
            step_id=step.step_id,
            artifact=artifact,
        ),
        RunCompletedPayload(
            event_type=RunEventType.RUN_COMPLETED,
            run_id=run.run_id,
            final_status=RunStatus.SUCCEEDED,
            completed_at=timestamp,
            grade_result=GradeResult(
                grade_id="grade_final",
                outcome=GradeOutcome.PASSED,
                score=1.0,
                summary="Dummy run completed successfully.",
                evidence_artifact_ids=[artifact.artifact_id],
            ),
        ),
    ]

    for index, payload in enumerate(payloads, start=1):
        event = RunEvent(
            event_id=f"evt_{index:03d}",
            run_id=run.run_id,
            sequence=index,
            occurred_at=timestamp,
            source=RunEventSource.SYSTEM,
            actor_type=ActorType.SYSTEM,
            event_type=payload.event_type,
            payload=payload,
        )

        assert event.event_type == payload.event_type


def test_models_reject_unexpected_fields() -> None:
    with pytest.raises(ValidationError):
        Run.model_validate(
            {
                **_run().model_dump(mode="json"),
                "unexpected": "value",
            }
        )


def test_grade_result_rejects_invalid_score_range() -> None:
    with pytest.raises(ValidationError):
        GradeResult(
            outcome=GradeOutcome.PASSED,
            score=1.5,
            summary="Invalid score.",
        )
