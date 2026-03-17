from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import cast

from pydantic import Field

from atlas_core.bastion import ApprovalRequestRef, AuditRecordEnvelope
from atlas_core.domain import (
    AtlasModel,
    Artifact,
    CURRENT_SCHEMA_VERSION,
    GradeResult,
    PolicyDecision,
    Run,
    RunCompletedPayload,
    RunCreatedPayload,
    RunEvent,
    RunEventType,
    RunStepCreatedPayload,
    ToolCall,
    ToolCallRecordedPayload,
)


class ReplayTimelineEntryKind(StrEnum):
    LIFECYCLE = "lifecycle"
    STEP = "step"
    TOOL_ACTION = "tool_action"
    APPROVAL = "approval"
    AUDIT = "audit"
    ARTIFACT = "artifact"
    OUTCOME = "outcome"


class ReplayTimelineEntryStatus(StrEnum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    FAILED = "failed"
    BLOCKED = "blocked"
    WAITING = "waiting"


class ReplayArtifactRef(AtlasModel):
    artifact_id: str
    event_id: str | None = None
    timeline_entry_id: str | None = None
    step_id: str | None = None
    created_at: datetime
    kind: str
    uri: str
    content_type: str
    display_name: str | None = None
    description: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class ReplayToolAction(AtlasModel):
    tool_action_id: str
    event_id: str
    sequence: int = Field(ge=0)
    occurred_at: datetime
    step_id: str | None = None
    request_id: str | None = None
    tool_call: ToolCall
    policy_decision: PolicyDecision | None = None
    artifact_ids: list[str] = Field(default_factory=list)


class ReplayPolicyDecision(AtlasModel):
    policy_decision_id: str
    event_id: str
    sequence: int = Field(ge=0)
    occurred_at: datetime
    tool_action_id: str | None = None
    decision: PolicyDecision


class ReplayApproval(AtlasModel):
    approval_request_id: str
    request: ApprovalRequestRef
    requested_event_id: str | None = None
    waiting_event_id: str | None = None
    resolved_event_id: str | None = None
    resumed_event_id: str | None = None
    requested_at: datetime
    waiting_at: datetime | None = None
    decided_at: datetime | None = None
    resumed_at: datetime | None = None
    operator_id: str | None = None


class ReplayAuditRecord(AtlasModel):
    audit_id: str
    event_id: str
    sequence: int = Field(ge=0)
    occurred_at: datetime
    step_id: str | None = None
    request_id: str | None = None
    event_kind: str
    actor_type: str
    payload: dict[str, object] = Field(default_factory=dict)


class ReplayOutcome(AtlasModel):
    event_id: str | None = None
    sequence: int | None = Field(default=None, ge=0)
    final_status: str
    completed_at: datetime | None = None
    grade_result: GradeResult | None = None
    summary: str | None = None


class ReplayObjectiveStatus(StrEnum):
    MET = "met"
    NOT_MET = "not_met"
    INCOMPLETE = "incomplete"


class ReplayOutcomeCheck(AtlasModel):
    check_key: str
    label: str
    status: ReplayObjectiveStatus
    detail: str


class ReplayOutcomeExplanation(AtlasModel):
    objective: str | None = None
    objective_status: ReplayObjectiveStatus
    summary: str
    highlights: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    state_checks: list[ReplayOutcomeCheck] = Field(default_factory=list)


class ReplayTimelineEntry(AtlasModel):
    entry_id: str
    event_id: str | None = None
    sequence: int = Field(ge=0)
    occurred_at: datetime
    kind: ReplayTimelineEntryKind
    status: ReplayTimelineEntryStatus
    title: str
    summary: str
    event_type: str | None = None
    step_id: str | None = None
    tool_action_id: str | None = None
    approval_request_id: str | None = None
    audit_id: str | None = None
    artifact_id: str | None = None
    related_artifact_ids: list[str] = Field(default_factory=list)


class RunReplay(AtlasModel):
    schema_version: int = Field(default=CURRENT_SCHEMA_VERSION, ge=1)
    run: Run
    raw_event_count: int = Field(ge=0)
    timeline_entries: list[ReplayTimelineEntry] = Field(default_factory=list)
    artifacts: list[ReplayArtifactRef] = Field(default_factory=list)
    tool_actions: list[ReplayToolAction] = Field(default_factory=list)
    policy_decisions: list[ReplayPolicyDecision] = Field(default_factory=list)
    approvals: list[ReplayApproval] = Field(default_factory=list)
    audit_records: list[ReplayAuditRecord] = Field(default_factory=list)
    outcome: ReplayOutcome
    outcome_explanation: ReplayOutcomeExplanation | None = None


def build_run_replay(run: Run, events: list[RunEvent], artifacts: list[Artifact]) -> RunReplay:
    timeline_entries: list[ReplayTimelineEntry] = []
    replay_artifacts: dict[str, ReplayArtifactRef] = {}
    tool_actions: list[ReplayToolAction] = []
    policy_decisions: list[ReplayPolicyDecision] = []
    approvals: dict[str, ReplayApproval] = {}
    audit_records: list[ReplayAuditRecord] = []
    outcome = ReplayOutcome(
        final_status=run.status.value,
        completed_at=run.completed_at,
        grade_result=run.grade_result,
        summary=run.grade_result.summary if run.grade_result is not None else None,
    )

    for event in sorted(events, key=lambda item: item.sequence):
        if event.event_type == RunEventType.RUN_CREATED:
            payload = cast(RunCreatedPayload, event.payload)
            timeline_entries.append(
                _timeline_entry(
                    event,
                    kind=ReplayTimelineEntryKind.LIFECYCLE,
                    status=ReplayTimelineEntryStatus.INFO,
                    title="Run created",
                    summary=f"Created run for {payload.run.task.task_title}.",
                )
            )
            continue

        if event.event_type in {RunEventType.RUN_READY, RunEventType.RUN_STARTED, RunEventType.RUN_STOP_REQUESTED, RunEventType.RUN_WAITING_APPROVAL, RunEventType.RUN_RESUMED}:
            timeline_entries.append(_lifecycle_timeline_entry(event))
            if event.event_type == RunEventType.RUN_WAITING_APPROVAL:
                approval_request_id = str(getattr(event.payload, "approval_request_id"))
                approval = approvals.get(approval_request_id)
                if approval is not None:
                    approvals[approval_request_id] = approval.model_copy(
                        update={"waiting_event_id": event.event_id, "waiting_at": getattr(event.payload, "waiting_at")}
                    )
            elif event.event_type == RunEventType.RUN_RESUMED:
                approval_request_id = str(getattr(event.payload, "approval_request_id"))
                approval = approvals.get(approval_request_id)
                if approval is not None:
                    approvals[approval_request_id] = approval.model_copy(
                        update={"resumed_event_id": event.event_id, "resumed_at": getattr(event.payload, "resumed_at")}
                    )
            continue

        if event.event_type == RunEventType.RUN_STEP_CREATED:
            payload = cast(RunStepCreatedPayload, event.payload)
            timeline_entries.append(
                _timeline_entry(
                    event,
                    kind=ReplayTimelineEntryKind.STEP,
                    status=_step_status(payload.step.status.value),
                    title=payload.step.title,
                    summary=f"Recorded step {payload.step.step_index}.",
                    step_id=payload.step.step_id,
                )
            )
            continue

        if event.event_type == RunEventType.TOOL_CALL_RECORDED:
            payload = cast(ToolCallRecordedPayload, event.payload)
            artifact_ids = _artifact_ids_from_tool_call(payload.tool_call)
            tool_action = ReplayToolAction(
                tool_action_id=payload.tool_call.tool_call_id,
                event_id=event.event_id,
                sequence=event.sequence,
                occurred_at=event.occurred_at,
                step_id=payload.step_id,
                request_id=event.correlation_id,
                tool_call=payload.tool_call,
                policy_decision=payload.policy_decision,
                artifact_ids=artifact_ids,
            )
            tool_actions.append(tool_action)
            timeline_entries.append(
                _timeline_entry(
                    event,
                    kind=ReplayTimelineEntryKind.TOOL_ACTION,
                    status=_tool_status(payload.tool_call.status.value),
                    title=f"{payload.tool_call.tool_name}.{payload.tool_call.action}",
                    summary=_tool_summary(payload.tool_call, payload.policy_decision),
                    step_id=payload.step_id,
                    tool_action_id=tool_action.tool_action_id,
                    related_artifact_ids=artifact_ids,
                )
            )
            if payload.policy_decision is not None:
                policy_decisions.append(
                    ReplayPolicyDecision(
                        policy_decision_id=payload.policy_decision.decision_id,
                        event_id=event.event_id,
                        sequence=event.sequence,
                        occurred_at=event.occurred_at,
                        tool_action_id=tool_action.tool_action_id,
                        decision=payload.policy_decision,
                    )
                )
            continue

        if event.event_type == RunEventType.APPROVAL_REQUESTED:
            approval = ApprovalRequestRef.model_validate(getattr(event.payload, "approval_request"))
            approvals[approval.approval_request_id] = ReplayApproval(
                approval_request_id=approval.approval_request_id,
                request=approval,
                requested_event_id=event.event_id,
                requested_at=approval.requested_at,
            )
            timeline_entries.append(
                _timeline_entry(
                    event,
                    kind=ReplayTimelineEntryKind.APPROVAL,
                    status=ReplayTimelineEntryStatus.WAITING,
                    title=f"Approval requested: {approval.requested_action_type}",
                    summary=approval.summary or "Execution paused pending operator approval.",
                    step_id=approval.step_id,
                    approval_request_id=approval.approval_request_id,
                )
            )
            continue

        if event.event_type == RunEventType.APPROVAL_RESOLVED:
            approval = ApprovalRequestRef.model_validate(getattr(event.payload, "approval_request"))
            operator_id = str(getattr(event.payload, "operator_id"))
            existing = approvals.get(approval.approval_request_id)
            approvals[approval.approval_request_id] = (
                existing.model_copy(
                    update={
                        "request": approval,
                        "resolved_event_id": event.event_id,
                        "decided_at": getattr(event.payload, "decided_at"),
                        "operator_id": operator_id,
                    }
                )
                if existing is not None
                else ReplayApproval(
                    approval_request_id=approval.approval_request_id,
                    request=approval,
                    requested_at=approval.requested_at,
                    resolved_event_id=event.event_id,
                    decided_at=getattr(event.payload, "decided_at"),
                    operator_id=operator_id,
                )
            )
            timeline_entries.append(
                _timeline_entry(
                    event,
                    kind=ReplayTimelineEntryKind.APPROVAL,
                    status=_approval_status(approval.status.value),
                    title=f"Approval {approval.status.value}",
                    summary=approval.resolution_summary or f"Operator {operator_id} resolved the approval request.",
                    step_id=approval.step_id,
                    approval_request_id=approval.approval_request_id,
                )
            )
            continue

        if event.event_type == RunEventType.AUDIT_RECORDED:
            audit = AuditRecordEnvelope.model_validate(getattr(event.payload, "audit_record"))
            audit_records.append(
                ReplayAuditRecord(
                    audit_id=audit.audit_id,
                    event_id=event.event_id,
                    sequence=event.sequence,
                    occurred_at=event.occurred_at,
                    step_id=audit.step_id,
                    request_id=audit.request_id,
                    event_kind=audit.event_kind.value,
                    actor_type=audit.actor_type.value,
                    payload=cast(dict[str, object], audit.payload),
                )
            )
            timeline_entries.append(
                _timeline_entry(
                    event,
                    kind=ReplayTimelineEntryKind.AUDIT,
                    status=ReplayTimelineEntryStatus.INFO,
                    title=f"Audit: {audit.event_kind.value}",
                    summary=_audit_summary(audit),
                    step_id=audit.step_id,
                    audit_id=audit.audit_id,
                )
            )
            continue

        if event.event_type == RunEventType.ARTIFACT_ATTACHED:
            artifact = getattr(event.payload, "artifact")
            artifact_ref = _artifact_ref(
                artifact=artifact,
                event_id=event.event_id,
                timeline_entry_id=f"timeline-{event.event_id}",
            )
            replay_artifacts[artifact_ref.artifact_id] = artifact_ref
            timeline_entries.append(
                _timeline_entry(
                    event,
                    kind=ReplayTimelineEntryKind.ARTIFACT,
                    status=ReplayTimelineEntryStatus.INFO,
                    title=f"Artifact attached: {artifact.kind.value}",
                    summary=artifact.display_name or artifact.uri,
                    step_id=artifact.step_id,
                    artifact_id=artifact.artifact_id,
                )
            )
            continue

        if event.event_type == RunEventType.RUN_COMPLETED:
            payload = cast(RunCompletedPayload, event.payload)
            outcome = ReplayOutcome(
                event_id=event.event_id,
                sequence=event.sequence,
                final_status=payload.final_status.value,
                completed_at=payload.completed_at,
                grade_result=payload.grade_result,
                summary=payload.grade_result.summary if payload.grade_result is not None else f"Run completed with status {payload.final_status.value}.",
            )
            timeline_entries.append(
                _timeline_entry(
                    event,
                    kind=ReplayTimelineEntryKind.OUTCOME,
                    status=_outcome_status(payload.final_status.value),
                    title=f"Run {payload.final_status.value}",
                    summary=outcome.summary or f"Run completed with status {payload.final_status.value}.",
                )
            )

    for artifact in artifacts:
        replay_artifacts.setdefault(
            artifact.artifact_id,
            _artifact_ref(artifact=artifact, event_id=None, timeline_entry_id=None),
        )

    replay = RunReplay(
        run=run,
        raw_event_count=len(events),
        timeline_entries=sorted(timeline_entries, key=lambda item: (item.sequence, item.entry_id)),
        artifacts=sorted(replay_artifacts.values(), key=lambda item: (item.created_at, item.artifact_id)),
        tool_actions=sorted(tool_actions, key=lambda item: (item.sequence, item.tool_action_id)),
        policy_decisions=sorted(policy_decisions, key=lambda item: (item.sequence, item.policy_decision_id)),
        approvals=sorted(approvals.values(), key=lambda item: (item.requested_at, item.approval_request_id)),
        audit_records=sorted(audit_records, key=lambda item: (item.sequence, item.audit_id)),
        outcome=outcome,
    )
    return replay.model_copy(
        update={"outcome_explanation": build_replay_outcome_explanation(replay)}
    )


def build_replay_outcome_explanation(
    replay: RunReplay,
    *,
    objective: str | None = None,
) -> ReplayOutcomeExplanation:
    state_checks = _state_checks_from_grade(replay.outcome.grade_result)
    highlights: list[str] = []
    blockers: list[str] = []

    for decision in replay.policy_decisions:
        if decision.decision.outcome.value == "deny":
            highlights.append(f"Bastion blocked {decision.decision.action_type}.")
        elif decision.decision.outcome.value == "require_approval":
            highlights.append(
                f"Bastion paused {decision.decision.action_type} for operator approval."
            )

    for approval in replay.approvals:
        if approval.request.status.value == "approved":
            highlights.append(
                f"Operator approved {approval.request.requested_action_type}."
            )
        elif approval.request.status.value in {"rejected", "expired", "cancelled"}:
            blockers.append(
                f"Approval for {approval.request.requested_action_type} ended as {approval.request.status.value}."
            )

    if replay.outcome.final_status == "waiting_approval":
        blockers.append("The run is paused until an operator resolves the pending approval.")
    elif replay.outcome.final_status == "failed":
        blockers.append("The run failed before all expected state changes were confirmed.")
    elif replay.outcome.final_status == "cancelled":
        blockers.append("The run was interrupted before the task objective was completed.")

    for check in state_checks:
        if check.status == ReplayObjectiveStatus.NOT_MET:
            blockers.append(f"Deterministic check failed: {check.label}.")

    return ReplayOutcomeExplanation(
        objective=objective,
        objective_status=_objective_status_for_replay(replay, state_checks),
        summary=_outcome_summary(replay, state_checks),
        highlights=_dedupe_preserve_order(highlights),
        blockers=_dedupe_preserve_order(blockers),
        state_checks=state_checks,
    )


def _timeline_entry(
    event: RunEvent,
    *,
    kind: ReplayTimelineEntryKind,
    status: ReplayTimelineEntryStatus,
    title: str,
    summary: str,
    step_id: str | None = None,
    tool_action_id: str | None = None,
    approval_request_id: str | None = None,
    audit_id: str | None = None,
    artifact_id: str | None = None,
    related_artifact_ids: list[str] | None = None,
) -> ReplayTimelineEntry:
    return ReplayTimelineEntry(
        entry_id=f"timeline-{event.event_id}",
        event_id=event.event_id,
        sequence=event.sequence,
        occurred_at=event.occurred_at,
        kind=kind,
        status=status,
        title=title,
        summary=summary,
        event_type=event.event_type.value,
        step_id=step_id,
        tool_action_id=tool_action_id,
        approval_request_id=approval_request_id,
        audit_id=audit_id,
        artifact_id=artifact_id,
        related_artifact_ids=related_artifact_ids or [],
    )


def _lifecycle_timeline_entry(event: RunEvent) -> ReplayTimelineEntry:
    if event.event_type == RunEventType.RUN_READY:
        return _timeline_entry(
            event,
            kind=ReplayTimelineEntryKind.LIFECYCLE,
            status=ReplayTimelineEntryStatus.INFO,
            title="Run ready",
            summary="Run is ready for execution.",
        )
    if event.event_type == RunEventType.RUN_STARTED:
        return _timeline_entry(
            event,
            kind=ReplayTimelineEntryKind.LIFECYCLE,
            status=ReplayTimelineEntryStatus.INFO,
            title="Run started",
            summary="Agent execution started.",
        )
    if event.event_type == RunEventType.RUN_STOP_REQUESTED:
        return _timeline_entry(
            event,
            kind=ReplayTimelineEntryKind.LIFECYCLE,
            status=ReplayTimelineEntryStatus.WARNING,
            title="Stop requested",
            summary="Operator requested the kill switch for this run.",
        )
    if event.event_type == RunEventType.RUN_WAITING_APPROVAL:
        return _timeline_entry(
            event,
            kind=ReplayTimelineEntryKind.LIFECYCLE,
            status=ReplayTimelineEntryStatus.WAITING,
            title="Waiting for approval",
            summary="Run is paused pending operator approval.",
            approval_request_id=str(getattr(event.payload, "approval_request_id")),
        )
    return _timeline_entry(
        event,
        kind=ReplayTimelineEntryKind.LIFECYCLE,
        status=ReplayTimelineEntryStatus.INFO,
        title="Run resumed",
        summary="Run resumed after operator action.",
        approval_request_id=str(getattr(event.payload, "approval_request_id")),
    )


def _tool_summary(tool_call: ToolCall, policy_decision: PolicyDecision | None) -> str:
    if policy_decision is None:
        return f"{tool_call.status.value.replace('_', ' ')} via tool execution."
    if policy_decision.outcome.value == "deny":
        return f"Denied by Bastion: {policy_decision.rationale}."
    if policy_decision.outcome.value == "require_approval":
        return f"Approval required: {policy_decision.rationale}."
    return f"Allowed by Bastion: {policy_decision.rationale}."


_CHECK_LABELS = {
    "ticket_status": "Ticket status updated",
    "ticket_note_terms": "Ticket notes include verification evidence",
    "doc_evidence": "Required SOP or wiki evidence consulted",
    "inbox_context": "Inbox context reviewed",
    "completed_checks": "Required verification checks completed",
    "approval_actions": "Approval-gated action completed",
    "forbidden_actions": "Forbidden shortcut avoided",
    "account_locked": "Account lock state",
    "mfa_enrolled": "MFA enrollment state",
    "is_admin": "Admin access state",
    "required_groups": "Required group membership",
    "forbidden_groups": "Forbidden group membership avoided",
    "device_compromised": "Device compromise state",
    "signal_disposition": "Suspicious-login signal disposition",
}


def _state_checks_from_grade(grade_result: GradeResult | None) -> list[ReplayOutcomeCheck]:
    if grade_result is None:
        return []
    raw_checks = grade_result.details.get("checks")
    if not isinstance(raw_checks, list):
        return []

    state_checks: list[ReplayOutcomeCheck] = []
    for raw_check in raw_checks:
        if not isinstance(raw_check, dict):
            continue
        name = raw_check.get("name")
        detail = raw_check.get("detail")
        passed = raw_check.get("passed")
        if not isinstance(name, str) or not isinstance(detail, str) or not isinstance(passed, bool):
            continue
        state_checks.append(
            ReplayOutcomeCheck(
                check_key=name,
                label=_CHECK_LABELS.get(name, name.replace("_", " ")),
                status=(
                    ReplayObjectiveStatus.MET
                    if passed
                    else ReplayObjectiveStatus.NOT_MET
                ),
                detail=detail,
            )
        )
    return state_checks


def _objective_status_for_replay(
    replay: RunReplay,
    state_checks: list[ReplayOutcomeCheck],
) -> ReplayObjectiveStatus:
    grade_result = replay.outcome.grade_result
    if (
        replay.outcome.final_status == "succeeded"
        and grade_result is not None
        and grade_result.outcome.value == "passed"
    ):
        return ReplayObjectiveStatus.MET
    if (
        grade_result is not None
        and grade_result.outcome.value == "failed"
        and replay.outcome.final_status in {"succeeded", "failed", "cancelled"}
    ):
        return ReplayObjectiveStatus.NOT_MET
    if state_checks and all(
        check.status == ReplayObjectiveStatus.MET for check in state_checks
    ):
        return ReplayObjectiveStatus.MET
    return ReplayObjectiveStatus.INCOMPLETE


def _outcome_summary(
    replay: RunReplay,
    state_checks: list[ReplayOutcomeCheck],
) -> str:
    objective_status = _objective_status_for_replay(replay, state_checks)
    if objective_status == ReplayObjectiveStatus.MET:
        return "The task objective was met and the deterministic state checks passed."
    if objective_status == ReplayObjectiveStatus.NOT_MET:
        failed_count = len(
            [check for check in state_checks if check.status == ReplayObjectiveStatus.NOT_MET]
        )
        if failed_count > 0:
            return f"The run ended without meeting the task objective. {failed_count} deterministic state checks failed."
        return "The run ended without meeting the task objective."
    if replay.outcome.final_status == "waiting_approval":
        return "The task remains incomplete because the run is waiting for operator approval."
    if replay.outcome.final_status == "failed":
        return "The task remains incomplete because the run failed before the expected state changes were confirmed."
    if replay.outcome.final_status == "cancelled":
        return "The task remains incomplete because the run was interrupted before completion."
    return "The task outcome is still incomplete or not yet fully explained by deterministic state checks."


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _audit_summary(audit: AuditRecordEnvelope) -> str:
    if audit.request_id:
        return f"Audit record for request {audit.request_id}."
    return "Audit record emitted by Bastion or operator flow."


def _artifact_ref(
    *,
    artifact: Artifact,
    event_id: str | None,
    timeline_entry_id: str | None,
) -> ReplayArtifactRef:
    return ReplayArtifactRef(
        artifact_id=artifact.artifact_id,
        event_id=event_id,
        timeline_entry_id=timeline_entry_id,
        step_id=artifact.step_id,
        created_at=artifact.created_at,
        kind=artifact.kind.value,
        uri=artifact.uri,
        content_type=artifact.content_type,
        display_name=artifact.display_name,
        description=artifact.description,
        metadata=cast(dict[str, object], artifact.metadata),
    )


def _artifact_ids_from_tool_call(tool_call: ToolCall) -> list[str]:
    if not tool_call.result:
        return []
    artifact_ids = tool_call.result.get("artifactIds")
    if not isinstance(artifact_ids, list):
        return []
    return [artifact_id for artifact_id in artifact_ids if isinstance(artifact_id, str)]


def _step_status(status: str) -> ReplayTimelineEntryStatus:
    if status == "completed":
        return ReplayTimelineEntryStatus.SUCCESS
    if status == "failed":
        return ReplayTimelineEntryStatus.FAILED
    if status == "in_progress":
        return ReplayTimelineEntryStatus.INFO
    return ReplayTimelineEntryStatus.INFO


def _tool_status(status: str) -> ReplayTimelineEntryStatus:
    if status == "succeeded":
        return ReplayTimelineEntryStatus.SUCCESS
    if status == "blocked":
        return ReplayTimelineEntryStatus.BLOCKED
    if status == "failed":
        return ReplayTimelineEntryStatus.FAILED
    return ReplayTimelineEntryStatus.INFO


def _approval_status(status: str) -> ReplayTimelineEntryStatus:
    if status == "approved":
        return ReplayTimelineEntryStatus.SUCCESS
    if status == "rejected":
        return ReplayTimelineEntryStatus.BLOCKED
    return ReplayTimelineEntryStatus.WAITING


def _outcome_status(status: str) -> ReplayTimelineEntryStatus:
    if status == "succeeded":
        return ReplayTimelineEntryStatus.SUCCESS
    if status == "cancelled":
        return ReplayTimelineEntryStatus.WARNING
    return ReplayTimelineEntryStatus.FAILED
