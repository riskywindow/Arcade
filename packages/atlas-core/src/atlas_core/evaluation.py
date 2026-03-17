from __future__ import annotations

from datetime import datetime
from typing import cast

from pydantic import Field

from atlas_core.bastion import ApprovalRequestRef, ApprovalRequestStatus
from atlas_core.domain import (
    AtlasModel,
    Artifact,
    CURRENT_SCHEMA_VERSION,
    GradeOutcome,
    GradeResult,
    PolicyDecisionOutcome,
    Run,
    RunCompletedPayload,
    RunEvent,
    RunEventType,
    RunStartedPayload,
    ToolCallRecordedPayload,
)


class RunScorePolicyCounts(AtlasModel):
    allow: int = Field(default=0, ge=0)
    deny: int = Field(default=0, ge=0)
    require_approval: int = Field(default=0, ge=0)


class RunScoreApprovalCounts(AtlasModel):
    total: int = Field(default=0, ge=0)
    pending: int = Field(default=0, ge=0)
    approved: int = Field(default=0, ge=0)
    rejected: int = Field(default=0, ge=0)


class RunScoreGraderSummary(AtlasModel):
    rubric_version: str | None = None
    summary: str
    deterministic_check_count: int = Field(default=0, ge=0)
    failed_check_count: int = Field(default=0, ge=0)


class RunScoreSummary(AtlasModel):
    schema_version: int = Field(default=CURRENT_SCHEMA_VERSION, ge=1)
    run_id: str
    scenario_id: str
    task_id: str
    final_status: str
    passed: bool
    grade_outcome: str
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    step_count: int = Field(default=0, ge=0)
    tool_call_count: int = Field(default=0, ge=0)
    artifact_count: int = Field(default=0, ge=0)
    evidence_artifact_count: int = Field(default=0, ge=0)
    duration_seconds: int | None = Field(default=None, ge=0)
    policy_counts: RunScorePolicyCounts = Field(default_factory=RunScorePolicyCounts)
    approval_counts: RunScoreApprovalCounts = Field(default_factory=RunScoreApprovalCounts)
    grader_summary: RunScoreGraderSummary | None = None


def build_run_score_summary(
    run: Run,
    events: list[RunEvent],
    artifacts: list[Artifact],
) -> RunScoreSummary:
    step_count = 0
    tool_call_count = 0
    policy_counts = RunScorePolicyCounts()
    approvals: dict[str, ApprovalRequestStatus] = {}

    for event in events:
        if event.event_type == RunEventType.RUN_STEP_CREATED:
            step_count += 1
            continue

        if event.event_type == RunEventType.TOOL_CALL_RECORDED:
            tool_call_count += 1
            payload = cast(ToolCallRecordedPayload, event.payload)
            if payload.policy_decision is None:
                continue
            outcome = payload.policy_decision.outcome
            if outcome == PolicyDecisionOutcome.ALLOW:
                policy_counts = policy_counts.model_copy(update={"allow": policy_counts.allow + 1})
            elif outcome == PolicyDecisionOutcome.DENY:
                policy_counts = policy_counts.model_copy(update={"deny": policy_counts.deny + 1})
            elif outcome == PolicyDecisionOutcome.REQUIRE_APPROVAL:
                policy_counts = policy_counts.model_copy(
                    update={"require_approval": policy_counts.require_approval + 1}
                )
            continue

        if event.event_type in {
            RunEventType.APPROVAL_REQUESTED,
            RunEventType.APPROVAL_RESOLVED,
        }:
            approval = ApprovalRequestRef.model_validate(getattr(event.payload, "approval_request"))
            approvals[approval.approval_request_id] = approval.status

    grade_result = run.grade_result
    return RunScoreSummary(
        run_id=run.run_id,
        scenario_id=run.scenario.scenario_id,
        task_id=run.task.task_id,
        final_status=run.status.value,
        passed=_run_passed(run.status.value, grade_result),
        grade_outcome=(
            grade_result.outcome.value if grade_result is not None else GradeOutcome.NOT_GRADED.value
        ),
        score=grade_result.score if grade_result is not None else None,
        step_count=step_count,
        tool_call_count=tool_call_count,
        artifact_count=len(artifacts),
        evidence_artifact_count=len(
            {
                artifact_id
                for artifact_id in (
                    grade_result.evidence_artifact_ids if grade_result is not None else []
                )
            }
        ),
        duration_seconds=_duration_seconds(run, events),
        policy_counts=policy_counts,
        approval_counts=RunScoreApprovalCounts(
            total=len(approvals),
            pending=sum(
                1 for status in approvals.values() if status == ApprovalRequestStatus.PENDING
            ),
            approved=sum(
                1 for status in approvals.values() if status == ApprovalRequestStatus.APPROVED
            ),
            rejected=sum(
                1
                for status in approvals.values()
                if status
                in {
                    ApprovalRequestStatus.REJECTED,
                    ApprovalRequestStatus.EXPIRED,
                    ApprovalRequestStatus.CANCELLED,
                }
            ),
        ),
        grader_summary=_grader_summary(grade_result),
    )


def _run_passed(final_status: str, grade_result: GradeResult | None) -> bool:
    if grade_result is not None:
        return grade_result.outcome == GradeOutcome.PASSED
    return final_status == "succeeded"


def _duration_seconds(run: Run, events: list[RunEvent]) -> int | None:
    started_at = run.started_at or _started_at_from_events(events)
    completed_at = run.completed_at or _completed_at_from_events(events)
    if started_at is None or completed_at is None:
        return None
    return max(int((completed_at - started_at).total_seconds()), 0)


def _started_at_from_events(events: list[RunEvent]) -> datetime | None:
    for event in events:
        if event.event_type == RunEventType.RUN_STARTED:
            payload = cast(RunStartedPayload, event.payload)
            return payload.started_at
    return None


def _completed_at_from_events(events: list[RunEvent]) -> datetime | None:
    for event in reversed(events):
        if event.event_type == RunEventType.RUN_COMPLETED:
            payload = cast(RunCompletedPayload, event.payload)
            return payload.completed_at
    return None


def _grader_summary(grade_result: GradeResult | None) -> RunScoreGraderSummary | None:
    if grade_result is None:
        return None
    checks = grade_result.details.get("checks")
    deterministic_check_count = len(checks) if isinstance(checks, list) else 0
    failed_checks = grade_result.details.get("failedChecks")
    if isinstance(failed_checks, list):
        failed_check_count = len(failed_checks)
    elif isinstance(checks, list):
        failed_check_count = sum(
            1
            for check in checks
            if isinstance(check, dict) and check.get("passed") is False
        )
    else:
        failed_check_count = 0
    return RunScoreGraderSummary(
        rubric_version=grade_result.rubric_version,
        summary=grade_result.summary,
        deterministic_check_count=deterministic_check_count,
        failed_check_count=failed_check_count,
    )
