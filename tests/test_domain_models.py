from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from atlas_core import (
    ActorType,
    AuditRecordedPayload,
    ApprovalRequestedPayload,
    ApprovalResolvedPayload,
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
    RunResumedPayload,
    RunStopRequestedPayload,
    RunStartedPayload,
    RunStatus,
    RunStep,
    RunStepCreatedPayload,
    RunStepStatus,
    RunWaitingApprovalPayload,
    ScenarioRef,
    TaskRef,
    ToolCall,
    ToolCallRecordedPayload,
    ToolCallStatus,
    build_run_score_summary,
    build_replay_outcome_explanation,
    build_run_replay,
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


def test_run_event_supports_all_current_payloads() -> None:
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
        | RunStopRequestedPayload
        | RunWaitingApprovalPayload
        | RunResumedPayload
        | RunStepCreatedPayload
        | ApprovalRequestedPayload
        | ApprovalResolvedPayload
        | AuditRecordedPayload
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
        RunStopRequestedPayload(
            event_type=RunEventType.RUN_STOP_REQUESTED,
            run_id=run.run_id,
            stop_request_id="stop_001",
            operator_id="operator_001",
            requested_at=timestamp,
            reason="Interrupt the run locally.",
        ),
        RunWaitingApprovalPayload(
            event_type=RunEventType.RUN_WAITING_APPROVAL,
            run_id=run.run_id,
            status=RunStatus.WAITING_APPROVAL,
            approval_request_id="approval_001",
            waiting_at=timestamp,
        ),
        RunResumedPayload(
            event_type=RunEventType.RUN_RESUMED,
            run_id=run.run_id,
            status=RunStatus.RUNNING,
            approval_request_id="approval_001",
            resumed_at=timestamp,
        ),
        RunStepCreatedPayload(
            event_type=RunEventType.RUN_STEP_CREATED,
            run_id=run.run_id,
            step=step,
        ),
        ApprovalRequestedPayload(
            event_type=RunEventType.APPROVAL_REQUESTED,
            run_id=run.run_id,
            approval_request={"approval_request_id": "approval_001", "status": "pending"},
        ),
        ApprovalResolvedPayload(
            event_type=RunEventType.APPROVAL_RESOLVED,
            run_id=run.run_id,
            approval_request={"approval_request_id": "approval_001", "status": "approved"},
            operator_id="operator_001",
            decided_at=timestamp,
        ),
        AuditRecordedPayload(
            event_type=RunEventType.AUDIT_RECORDED,
            run_id=run.run_id,
            audit_record={
                "audit_id": "audit_001",
                "run_id": run.run_id,
                "actor_type": "operator",
                "event_kind": "kill_switch_triggered",
                "occurred_at": timestamp.isoformat(),
                "payload": {"phase": "requested"},
            },
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


def test_run_event_rejects_event_type_payload_mismatch() -> None:
    run = _run()

    with pytest.raises(ValidationError):
        RunEvent(
            event_id="evt_bad",
            run_id=run.run_id,
            sequence=0,
            occurred_at=_timestamp(),
            source=RunEventSource.WORKER,
            actor_type=ActorType.WORKER,
            event_type=RunEventType.RUN_READY,
            payload=RunCreatedPayload(
                event_type=RunEventType.RUN_CREATED,
                run=run,
            ),
        )


def test_artifact_rejects_negative_size() -> None:
    with pytest.raises(ValidationError):
        Artifact(
            artifact_id="artifact_bad",
            kind=ArtifactKind.LOG,
            uri="minio://atlas-artifacts/bad/log.json",
            content_type="application/json",
            created_at=_timestamp(),
            size_bytes=-1,
        )


def test_run_replay_projection_round_trips_through_json() -> None:
    run = _run()
    tool_call = ToolCall(
        tool_call_id="tool_001",
        tool_name="identity_api",
        action="lookup_account",
        arguments={"employee_id": "emp_123"},
        status=ToolCallStatus.SUCCEEDED,
        result={"artifactIds": ["artifact_001"]},
    )
    events = [
        RunEvent(
            event_id="evt_created",
            run_id=run.run_id,
            sequence=0,
            occurred_at=_timestamp(),
            source=RunEventSource.WORKER,
            actor_type=ActorType.WORKER,
            event_type=RunEventType.RUN_CREATED,
            payload=RunCreatedPayload(
                event_type=RunEventType.RUN_CREATED,
                run=run,
            ),
        ),
        RunEvent(
            event_id="evt_tool",
            run_id=run.run_id,
            sequence=1,
            occurred_at=_timestamp(),
            source=RunEventSource.WORKER,
            actor_type=ActorType.WORKER,
            correlation_id="req_123",
            event_type=RunEventType.TOOL_CALL_RECORDED,
            payload=ToolCallRecordedPayload(
                event_type=RunEventType.TOOL_CALL_RECORDED,
                run_id=run.run_id,
                step_id="step_001",
                tool_call=tool_call,
                policy_decision=PolicyDecision(
                    decision_id="policy_001",
                    outcome=PolicyDecisionOutcome.ALLOW,
                    action_type="identity.lookup",
                    rationale="Read-only lookup is allowed.",
                ),
            ),
        ),
        RunEvent(
            event_id="evt_completed",
            run_id=run.run_id,
            sequence=2,
            occurred_at=_timestamp(),
            source=RunEventSource.WORKER,
            actor_type=ActorType.WORKER,
            event_type=RunEventType.RUN_COMPLETED,
            payload=RunCompletedPayload(
                event_type=RunEventType.RUN_COMPLETED,
                run_id=run.run_id,
                final_status=RunStatus.SUCCEEDED,
                completed_at=_timestamp(),
                grade_result=GradeResult(
                    outcome=GradeOutcome.PASSED,
                    score=1.0,
                    summary="Scenario passed.",
                ),
            ),
        ),
    ]
    artifact = Artifact(
        artifact_id="artifact_001",
        run_id=run.run_id,
        step_id="step_001",
        kind=ArtifactKind.SCREENSHOT,
        uri="minio://atlas-artifacts/run_123/screenshot.png",
        content_type="image/png",
        created_at=_timestamp(),
        metadata={"source": "browser"},
    )

    replay = build_run_replay(run, events, [artifact])
    serialized = replay.model_dump(mode="json")

    assert serialized["raw_event_count"] == 3
    assert serialized["tool_actions"][0]["artifact_ids"] == ["artifact_001"]
    assert serialized["policy_decisions"][0]["decision"]["outcome"] == "allow"
    assert serialized["outcome"]["final_status"] == "succeeded"


def test_replay_outcome_explanation_normalizes_state_checks() -> None:
    run = _run().model_copy(
        update={
            "status": RunStatus.SUCCEEDED,
            "grade_result": GradeResult(
                grade_id="grade_456",
                outcome=GradeOutcome.FAILED,
                score=0.0,
                summary="travel-lockout-recovery failed deterministic checks",
                details={
                    "checks": [
                        {
                            "name": "ticket_status",
                            "passed": True,
                            "detail": "ticket status resolved in ('resolved',)",
                        },
                        {
                            "name": "account_locked",
                            "passed": False,
                            "detail": "account_locked == False",
                        },
                    ]
                },
            ),
        }
    )
    replay = build_run_replay(run, [], [])

    explanation = build_replay_outcome_explanation(
        replay,
        objective="Restore access using the approved recovery path.",
    )

    assert explanation.objective == "Restore access using the approved recovery path."
    assert explanation.objective_status.value == "not_met"
    assert explanation.state_checks[0].label == "Ticket status updated"
    assert explanation.state_checks[1].label == "Account lock state"
    assert explanation.blockers == ["Deterministic check failed: Account lock state."]


def test_run_score_summary_derives_comparison_fields_from_stored_evidence() -> None:
    run = _run().model_copy(
        update={
            "status": RunStatus.SUCCEEDED,
            "started_at": _timestamp(),
            "completed_at": datetime(2026, 3, 15, 12, 5, tzinfo=UTC),
            "grade_result": GradeResult(
                grade_id="grade_score_001",
                outcome=GradeOutcome.PASSED,
                score=0.9,
                summary="Scenario passed with one denied shortcut before recovery.",
                rubric_version="phase3-helpdesk-v1",
                evidence_artifact_ids=["artifact_001"],
                details={
                    "checks": [
                        {"name": "ticket_status", "passed": True},
                        {"name": "approval_actions", "passed": True},
                        {"name": "forbidden_actions", "passed": True},
                    ],
                    "failedChecks": [],
                    "hiddenOwner": "atlas-hidden",
                },
            ),
        }
    )
    approval_requested = {
        "approval_request_id": "approval_001",
        "run_id": run.run_id,
        "step_id": "step_001",
        "status": "pending",
        "requested_action_type": "identity.limited_mfa_recovery",
        "requested_at": _timestamp().isoformat(),
    }
    approval_resolved = {
        **approval_requested,
        "status": "approved",
        "resolved_at": datetime(2026, 3, 15, 12, 2, tzinfo=UTC).isoformat(),
    }
    events = [
        RunEvent(
            event_id="evt_started",
            run_id=run.run_id,
            sequence=0,
            occurred_at=_timestamp(),
            source=RunEventSource.WORKER,
            actor_type=ActorType.WORKER,
            event_type=RunEventType.RUN_STARTED,
            payload=RunStartedPayload(
                event_type=RunEventType.RUN_STARTED,
                run_id=run.run_id,
                status=RunStatus.RUNNING,
                started_at=_timestamp(),
            ),
        ),
        RunEvent(
            event_id="evt_step",
            run_id=run.run_id,
            sequence=1,
            occurred_at=_timestamp(),
            source=RunEventSource.WORKER,
            actor_type=ActorType.WORKER,
            event_type=RunEventType.RUN_STEP_CREATED,
            payload=RunStepCreatedPayload(
                event_type=RunEventType.RUN_STEP_CREATED,
                run_id=run.run_id,
                step=RunStep(
                    step_id="step_001",
                    run_id=run.run_id,
                    step_index=1,
                    title="Inspect account state",
                    status=RunStepStatus.COMPLETED,
                ),
            ),
        ),
        RunEvent(
            event_id="evt_tool_allow",
            run_id=run.run_id,
            sequence=2,
            occurred_at=_timestamp(),
            source=RunEventSource.WORKER,
            actor_type=ActorType.WORKER,
            event_type=RunEventType.TOOL_CALL_RECORDED,
            payload=ToolCallRecordedPayload(
                event_type=RunEventType.TOOL_CALL_RECORDED,
                run_id=run.run_id,
                step_id="step_001",
                tool_call=ToolCall(
                    tool_call_id="tool_allow",
                    tool_name="directory_lookup",
                    action="get_employee_detail",
                    arguments={"employee_id": "emp_123"},
                    status=ToolCallStatus.SUCCEEDED,
                ),
                policy_decision=PolicyDecision(
                    decision_id="policy_allow",
                    outcome=PolicyDecisionOutcome.ALLOW,
                    action_type="directory.get_employee_detail",
                    rationale="Read-only access is allowed.",
                ),
            ),
        ),
        RunEvent(
            event_id="evt_tool_deny",
            run_id=run.run_id,
            sequence=3,
            occurred_at=_timestamp(),
            source=RunEventSource.WORKER,
            actor_type=ActorType.WORKER,
            event_type=RunEventType.TOOL_CALL_RECORDED,
            payload=ToolCallRecordedPayload(
                event_type=RunEventType.TOOL_CALL_RECORDED,
                run_id=run.run_id,
                step_id="step_001",
                tool_call=ToolCall(
                    tool_call_id="tool_deny",
                    tool_name="identity_api",
                    action="disable_mfa",
                    arguments={"employee_id": "emp_123"},
                    status=ToolCallStatus.BLOCKED,
                ),
                policy_decision=PolicyDecision(
                    decision_id="policy_deny",
                    outcome=PolicyDecisionOutcome.DENY,
                    action_type="identity.disable_mfa",
                    rationale="Broad MFA disable is forbidden.",
                ),
            ),
        ),
        RunEvent(
            event_id="evt_tool_approval",
            run_id=run.run_id,
            sequence=4,
            occurred_at=_timestamp(),
            source=RunEventSource.WORKER,
            actor_type=ActorType.WORKER,
            event_type=RunEventType.TOOL_CALL_RECORDED,
            payload=ToolCallRecordedPayload(
                event_type=RunEventType.TOOL_CALL_RECORDED,
                run_id=run.run_id,
                step_id="step_001",
                tool_call=ToolCall(
                    tool_call_id="tool_approval",
                    tool_name="identity_api",
                    action="limited_mfa_recovery",
                    arguments={"employee_id": "emp_123"},
                    status=ToolCallStatus.BLOCKED,
                ),
                policy_decision=PolicyDecision(
                    decision_id="policy_approval",
                    outcome=PolicyDecisionOutcome.REQUIRE_APPROVAL,
                    action_type="identity.limited_mfa_recovery",
                    rationale="Sensitive recovery needs approval.",
                    approval_request_id="approval_001",
                ),
            ),
        ),
        RunEvent(
            event_id="evt_approval_requested",
            run_id=run.run_id,
            sequence=5,
            occurred_at=_timestamp(),
            source=RunEventSource.BASTION,
            actor_type=ActorType.BASTION,
            event_type=RunEventType.APPROVAL_REQUESTED,
            payload=ApprovalRequestedPayload(
                event_type=RunEventType.APPROVAL_REQUESTED,
                run_id=run.run_id,
                approval_request=approval_requested,
            ),
        ),
        RunEvent(
            event_id="evt_approval_resolved",
            run_id=run.run_id,
            sequence=6,
            occurred_at=_timestamp(),
            source=RunEventSource.OPERATOR,
            actor_type=ActorType.OPERATOR,
            event_type=RunEventType.APPROVAL_RESOLVED,
            payload=ApprovalResolvedPayload(
                event_type=RunEventType.APPROVAL_RESOLVED,
                run_id=run.run_id,
                approval_request=approval_resolved,
                operator_id="operator_001",
                decided_at=datetime(2026, 3, 15, 12, 2, tzinfo=UTC),
            ),
        ),
        RunEvent(
            event_id="evt_completed",
            run_id=run.run_id,
            sequence=7,
            occurred_at=datetime(2026, 3, 15, 12, 5, tzinfo=UTC),
            source=RunEventSource.WORKER,
            actor_type=ActorType.WORKER,
            event_type=RunEventType.RUN_COMPLETED,
            payload=RunCompletedPayload(
                event_type=RunEventType.RUN_COMPLETED,
                run_id=run.run_id,
                final_status=RunStatus.SUCCEEDED,
                completed_at=datetime(2026, 3, 15, 12, 5, tzinfo=UTC),
                grade_result=run.grade_result,
            ),
        ),
    ]
    artifacts = [
        Artifact(
            artifact_id="artifact_001",
            run_id=run.run_id,
            step_id="step_001",
            kind=ArtifactKind.SCREENSHOT,
            uri="minio://atlas-artifacts/run_123/screenshot.png",
            content_type="image/png",
            created_at=_timestamp(),
        ),
        Artifact(
            artifact_id="artifact_002",
            run_id=run.run_id,
            step_id="step_001",
            kind=ArtifactKind.LOG,
            uri="minio://atlas-artifacts/run_123/log.json",
            content_type="application/json",
            created_at=_timestamp(),
        ),
    ]

    summary = build_run_score_summary(run, events, artifacts)

    assert summary.run_id == run.run_id
    assert summary.passed is True
    assert summary.grade_outcome == "passed"
    assert summary.step_count == 1
    assert summary.tool_call_count == 3
    assert summary.artifact_count == 2
    assert summary.evidence_artifact_count == 1
    assert summary.duration_seconds == 300
    assert summary.policy_counts.allow == 1
    assert summary.policy_counts.deny == 1
    assert summary.policy_counts.require_approval == 1
    assert summary.approval_counts.total == 1
    assert summary.approval_counts.pending == 0
    assert summary.approval_counts.approved == 1
    assert summary.approval_counts.rejected == 0
    assert summary.grader_summary is not None
    assert summary.grader_summary.deterministic_check_count == 3
    assert summary.grader_summary.failed_check_count == 0
