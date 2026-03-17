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

    return RunReplay(
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
