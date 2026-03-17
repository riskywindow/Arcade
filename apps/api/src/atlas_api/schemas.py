from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from atlas_core.domain import (
    ActorType,
    ArtifactKind,
    GradeOutcome,
    PolicyDecisionOutcome,
    RunEventType,
    RunEventSource,
    RunStatus,
    RunStepStatus,
    ToolCallStatus,
)
from atlas_core.bastion import ApprovalRequestStatus
from atlas_env_helpdesk import NoteKind


def _to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(segment.capitalize() for segment in tail)


class ApiModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        alias_generator=_to_camel,
        use_enum_values=True,
    )


class EnvironmentRefSchema(ApiModel):
    environment_id: str
    environment_name: str
    environment_version: str | None = None


class ScenarioRefSchema(ApiModel):
    scenario_id: str
    environment_id: str
    scenario_name: str
    scenario_seed: str


class TaskRefSchema(ApiModel):
    task_id: str
    scenario_id: str
    task_kind: str
    task_title: str


class RunStepSchema(ApiModel):
    step_id: str
    run_id: str
    step_index: int = Field(ge=0)
    title: str
    status: RunStepStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None


class ToolCallSchema(ApiModel):
    tool_call_id: str
    tool_name: str
    action: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: ToolCallStatus
    result: dict[str, Any] | None = None
    error_message: str | None = None


class PolicyDecisionSchema(ApiModel):
    decision_id: str
    outcome: PolicyDecisionOutcome
    action_type: str
    rationale: str
    approval_request_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApprovalRequestSchema(ApiModel):
    approval_request_id: str
    run_id: str
    step_id: str | None = None
    status: ApprovalRequestStatus
    requested_action_type: str
    tool_name: str | None = None
    requested_arguments: dict[str, Any] = Field(default_factory=dict)
    requester_role: str
    reason_code: str | None = None
    summary: str | None = None
    target_resource_type: str | None = None
    target_resource_id: str | None = None
    requested_at: datetime
    expires_at: datetime | None = None
    resolved_at: datetime | None = None
    resolution_summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactSchema(ApiModel):
    schema_version: int = 1
    artifact_id: str
    run_id: str | None = None
    step_id: str | None = None
    kind: ArtifactKind
    uri: str
    content_type: str
    created_at: datetime
    display_name: str | None = None
    description: str | None = None
    sha256: str | None = None
    size_bytes: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GradeResultSchema(ApiModel):
    grade_id: str | None = None
    outcome: GradeOutcome
    score: float | None = None
    summary: str
    rubric_version: str | None = None
    evidence_artifact_ids: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class RunScorePolicyCountsSchema(ApiModel):
    allow: int = 0
    deny: int = 0
    require_approval: int = 0


class RunScoreApprovalCountsSchema(ApiModel):
    total: int = 0
    pending: int = 0
    approved: int = 0
    rejected: int = 0


class RunScoreGraderSummarySchema(ApiModel):
    rubric_version: str | None = None
    summary: str
    deterministic_check_count: int = 0
    failed_check_count: int = 0


class RunScoreSummarySchema(ApiModel):
    schema_version: int = 1
    run_id: str
    scenario_id: str
    task_id: str
    final_status: RunStatus
    passed: bool
    grade_outcome: GradeOutcome
    score: float | None = None
    step_count: int = 0
    tool_call_count: int = 0
    artifact_count: int = 0
    evidence_artifact_count: int = 0
    duration_seconds: int | None = None
    policy_counts: RunScorePolicyCountsSchema = Field(default_factory=RunScorePolicyCountsSchema)
    approval_counts: RunScoreApprovalCountsSchema = Field(default_factory=RunScoreApprovalCountsSchema)
    grader_summary: RunScoreGraderSummarySchema | None = None


class RunSchema(ApiModel):
    run_id: str
    environment: EnvironmentRefSchema
    scenario: ScenarioRefSchema
    task: TaskRefSchema
    status: RunStatus
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    current_step_index: int
    active_agent_id: str | None = None
    grade_result: GradeResultSchema | None = None
    score_summary: RunScoreSummarySchema | None = None


class RunCreatedPayloadSchema(ApiModel):
    schema_version: int = 1
    event_type: RunEventType
    run: RunSchema


class RunReadyPayloadSchema(ApiModel):
    schema_version: int = 1
    event_type: RunEventType
    run_id: str
    status: RunStatus


class RunStartedPayloadSchema(ApiModel):
    schema_version: int = 1
    event_type: RunEventType
    run_id: str
    status: RunStatus
    started_at: datetime


class RunStopRequestedPayloadSchema(ApiModel):
    schema_version: int = 1
    event_type: RunEventType
    run_id: str
    stop_request_id: str
    operator_id: str
    requested_at: datetime
    reason: str | None = None


class RunWaitingApprovalPayloadSchema(ApiModel):
    schema_version: int = 1
    event_type: RunEventType
    run_id: str
    status: RunStatus
    approval_request_id: str
    waiting_at: datetime


class RunResumedPayloadSchema(ApiModel):
    schema_version: int = 1
    event_type: RunEventType
    run_id: str
    status: RunStatus
    approval_request_id: str
    resumed_at: datetime


class RunStepCreatedPayloadSchema(ApiModel):
    schema_version: int = 1
    event_type: RunEventType
    run_id: str
    step: RunStepSchema


class ToolCallRecordedPayloadSchema(ApiModel):
    schema_version: int = 1
    event_type: RunEventType
    run_id: str
    step_id: str | None = None
    tool_call: ToolCallSchema
    policy_decision: PolicyDecisionSchema | None = None


class ApprovalRequestedPayloadSchema(ApiModel):
    schema_version: int = 1
    event_type: RunEventType
    run_id: str
    approval_request: ApprovalRequestSchema


class ApprovalResolvedPayloadSchema(ApiModel):
    schema_version: int = 1
    event_type: RunEventType
    run_id: str
    approval_request: ApprovalRequestSchema
    operator_id: str
    decided_at: datetime


class AuditRecordSchema(ApiModel):
    audit_id: str
    run_id: str
    step_id: str | None = None
    request_id: str | None = None
    actor_type: ActorType
    event_kind: str
    occurred_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class AuditRecordedPayloadSchema(ApiModel):
    schema_version: int = 1
    event_type: RunEventType
    run_id: str
    audit_record: AuditRecordSchema


class ArtifactAttachedPayloadSchema(ApiModel):
    schema_version: int = 1
    event_type: RunEventType
    run_id: str
    step_id: str | None = None
    artifact: ArtifactSchema


class RunCompletedPayloadSchema(ApiModel):
    schema_version: int = 1
    event_type: RunEventType
    run_id: str
    final_status: RunStatus
    completed_at: datetime
    grade_result: GradeResultSchema | None = None


RunEventPayloadSchema = (
    RunCreatedPayloadSchema
    | RunReadyPayloadSchema
    | RunStartedPayloadSchema
    | RunStopRequestedPayloadSchema
    | RunWaitingApprovalPayloadSchema
    | RunResumedPayloadSchema
    | RunStepCreatedPayloadSchema
    | ApprovalRequestedPayloadSchema
    | ApprovalResolvedPayloadSchema
    | AuditRecordedPayloadSchema
    | ToolCallRecordedPayloadSchema
    | ArtifactAttachedPayloadSchema
    | RunCompletedPayloadSchema
)


class RunEventSchema(ApiModel):
    schema_version: int = 1
    event_id: str
    run_id: str
    sequence: int
    occurred_at: datetime
    source: RunEventSource
    actor_type: ActorType
    correlation_id: str | None = None
    event_type: RunEventType
    payload: RunEventPayloadSchema


class ReplayArtifactRefSchema(ApiModel):
    artifact_id: str
    event_id: str | None = None
    timeline_entry_id: str | None = None
    step_id: str | None = None
    created_at: datetime
    kind: ArtifactKind
    uri: str
    content_type: str
    display_name: str | None = None
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReplayToolActionSchema(ApiModel):
    tool_action_id: str
    event_id: str
    sequence: int
    occurred_at: datetime
    step_id: str | None = None
    request_id: str | None = None
    tool_call: ToolCallSchema
    policy_decision: PolicyDecisionSchema | None = None
    artifact_ids: list[str] = Field(default_factory=list)


class ReplayPolicyDecisionSchema(ApiModel):
    policy_decision_id: str
    event_id: str
    sequence: int
    occurred_at: datetime
    tool_action_id: str | None = None
    decision: PolicyDecisionSchema


class ReplayApprovalSchema(ApiModel):
    approval_request_id: str
    request: ApprovalRequestSchema
    requested_event_id: str | None = None
    waiting_event_id: str | None = None
    resolved_event_id: str | None = None
    resumed_event_id: str | None = None
    requested_at: datetime
    waiting_at: datetime | None = None
    decided_at: datetime | None = None
    resumed_at: datetime | None = None
    operator_id: str | None = None


class ReplayAuditRecordSchema(ApiModel):
    audit_id: str
    event_id: str
    sequence: int
    occurred_at: datetime
    step_id: str | None = None
    request_id: str | None = None
    event_kind: str
    actor_type: ActorType
    payload: dict[str, Any] = Field(default_factory=dict)


class ReplayOutcomeSchema(ApiModel):
    event_id: str | None = None
    sequence: int | None = None
    final_status: RunStatus
    completed_at: datetime | None = None
    grade_result: GradeResultSchema | None = None
    summary: str | None = None


class ReplayOutcomeCheckSchema(ApiModel):
    check_key: str
    label: str
    status: str
    detail: str


class ReplayOutcomeExplanationSchema(ApiModel):
    objective: str | None = None
    objective_status: str
    summary: str
    highlights: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    state_checks: list[ReplayOutcomeCheckSchema] = Field(default_factory=list)


class ReplayTimelineEntrySchema(ApiModel):
    entry_id: str
    event_id: str | None = None
    sequence: int
    occurred_at: datetime
    kind: str
    status: str
    title: str
    summary: str
    event_type: str | None = None
    step_id: str | None = None
    tool_action_id: str | None = None
    approval_request_id: str | None = None
    audit_id: str | None = None
    artifact_id: str | None = None
    related_artifact_ids: list[str] = Field(default_factory=list)


class RunReplaySchema(ApiModel):
    schema_version: int = 1
    run: RunSchema
    raw_event_count: int
    timeline_entries: list[ReplayTimelineEntrySchema] = Field(default_factory=list)
    artifacts: list[ReplayArtifactRefSchema] = Field(default_factory=list)
    tool_actions: list[ReplayToolActionSchema] = Field(default_factory=list)
    policy_decisions: list[ReplayPolicyDecisionSchema] = Field(default_factory=list)
    approvals: list[ReplayApprovalSchema] = Field(default_factory=list)
    audit_records: list[ReplayAuditRecordSchema] = Field(default_factory=list)
    outcome: ReplayOutcomeSchema
    outcome_explanation: ReplayOutcomeExplanationSchema | None = None
    score_summary: RunScoreSummarySchema | None = None


class CreateRunRequest(ApiModel):
    environment: EnvironmentRefSchema
    scenario: ScenarioRefSchema
    task: TaskRefSchema
    active_agent_id: str | None = None

    @model_validator(mode="after")
    def validate_environment_and_scenario_match(self) -> "CreateRunRequest":
        if self.environment.environment_id != self.scenario.environment_id:
            raise ValueError("environmentId must match scenario.environmentId")
        if self.scenario.scenario_id != self.task.scenario_id:
            raise ValueError("scenarioId must match task.scenarioId")
        return self


class RunResponse(ApiModel):
    run: RunSchema


class RunListResponse(ApiModel):
    runs: list[RunSchema]


class RunEventListResponse(ApiModel):
    run_id: str
    events: list[RunEventSchema]


class RunReplayResponse(ApiModel):
    replay: RunReplaySchema


class ArtifactListResponse(ApiModel):
    run_id: str
    artifacts: list[ArtifactSchema]


class AuditListResponse(ApiModel):
    run_id: str
    records: list[AuditRecordSchema]


class ApprovalListResponse(ApiModel):
    run_id: str
    approvals: list[ApprovalRequestSchema]


class ApprovalDecisionRequest(ApiModel):
    operator_id: str
    resolution_summary: str | None = None


class StopRunRequest(ApiModel):
    operator_id: str
    reason: str | None = None


class ApprovalResponse(ApiModel):
    approval: ApprovalRequestSchema


class StopRunResponse(ApiModel):
    run_id: str
    status: RunStatus
    stop_request_id: str
    requested_at: datetime


class EmployeeSummarySchema(ApiModel):
    employee_id: str
    display_name: str
    email: str
    title: str
    department_slug: str
    manager_employee_id: str | None = None


class DeviceSummarySchema(ApiModel):
    device_id: str
    employee_id: str
    hostname: str
    platform: str
    health_state: str
    compromised: bool
    assigned_at: datetime
    serial_number: str


class AccountAccessSummarySchema(ApiModel):
    account_id: str
    email: str
    account_locked: bool
    mfa_enrolled: bool
    groups: list[str] = Field(default_factory=list)
    is_admin: bool
    password_last_reset_at: datetime


class SuspiciousEventSummarySchema(ApiModel):
    event_id: str
    employee_id: str
    detected_at: datetime
    signal_type: str
    severity: str
    summary: str
    disposition: str


class TicketNoteSchema(ApiModel):
    note_id: str
    ticket_id: str
    author: str
    body: str
    kind: NoteKind
    created_at: datetime


class HelpdeskTicketSchema(ApiModel):
    ticket_id: str
    requester_employee_id: str
    assigned_team: str
    assigned_to: str | None = None
    status: str
    priority: str
    title: str
    summary: str
    created_at: datetime
    updated_at: datetime
    related_employee_id: str | None = None
    related_device_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    notes: list[TicketNoteSchema] = Field(default_factory=list)


class HelpdeskTicketDetailSchema(ApiModel):
    ticket: HelpdeskTicketSchema
    requester: EmployeeSummarySchema
    related_employee: EmployeeSummarySchema | None = None
    related_device: DeviceSummarySchema | None = None


class HelpdeskTicketQueueResponse(ApiModel):
    seed: str
    tickets: list[HelpdeskTicketSchema]


class HelpdeskTicketResponse(ApiModel):
    ticket: HelpdeskTicketSchema


class HelpdeskTicketDetailResponse(ApiModel):
    detail: HelpdeskTicketDetailSchema


class DirectoryEmployeeSchema(ApiModel):
    employee_id: str
    display_name: str
    email: str
    title: str
    department_slug: str
    employment_status: str
    location: str
    manager_employee_id: str | None = None
    start_date: datetime


class DirectoryEmployeeListResponse(ApiModel):
    seed: str
    employees: list[DirectoryEmployeeSchema]


class DirectoryEmployeeDetailSchema(ApiModel):
    employee: DirectoryEmployeeSchema
    manager: EmployeeSummarySchema | None = None
    devices: list[DeviceSummarySchema]
    account_access: AccountAccessSummarySchema
    related_tickets: list[HelpdeskTicketSchema]
    suspicious_events: list[SuspiciousEventSummarySchema]


class DirectoryEmployeeDetailResponse(ApiModel):
    detail: DirectoryEmployeeDetailSchema


class WikiDocumentSchema(ApiModel):
    page_id: str
    slug: str
    title: str
    category: str
    summary: str
    body: str
    updated_at: datetime


class WikiDocumentListResponse(ApiModel):
    seed: str
    documents: list[WikiDocumentSchema]


class WikiDocumentResponse(ApiModel):
    document: WikiDocumentSchema


class WikiSearchResultSchema(ApiModel):
    document: WikiDocumentSchema
    score: int
    matched_terms: list[str] = Field(default_factory=list)


class WikiSearchResponseSchema(ApiModel):
    seed: str
    query: str
    results: list[WikiSearchResultSchema]


class InboxMessageSchema(ApiModel):
    message_id: str
    sender: str
    sent_at: datetime
    subject: str
    body: str
    channel: str


class InboxThreadSchema(ApiModel):
    thread_id: str
    participant_emails: list[str]
    subject: str
    messages: list[InboxMessageSchema]
    last_message_at: datetime
    message_count: int


class InboxThreadListResponse(ApiModel):
    seed: str
    threads: list[InboxThreadSchema]


class InboxThreadResponse(ApiModel):
    thread: InboxThreadSchema


class AddTicketNoteRequest(ApiModel):
    author: str
    body: str
    kind: NoteKind = NoteKind.INTERNAL


class AssignTicketRequest(ApiModel):
    assigned_to: str | None = None


class TransitionTicketStatusRequest(ApiModel):
    status: str
