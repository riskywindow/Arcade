from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AtlasModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


CURRENT_SCHEMA_VERSION = 1


class RunStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunStepStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ToolCallStatus(StrEnum):
    REQUESTED = "requested"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"


class PolicyDecisionOutcome(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class ArtifactKind(StrEnum):
    LOG = "log"
    SCREENSHOT = "screenshot"
    TRACE = "trace"
    DIFF = "diff"
    REPORT = "report"
    NOTE = "note"


class GradeOutcome(StrEnum):
    NOT_GRADED = "not_graded"
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"


class RunEventType(StrEnum):
    RUN_CREATED = "run.created"
    RUN_READY = "run.ready"
    RUN_STARTED = "run.started"
    RUN_STEP_CREATED = "run.step.created"
    TOOL_CALL_RECORDED = "tool_call.recorded"
    ARTIFACT_ATTACHED = "artifact.attached"
    RUN_COMPLETED = "run.completed"


class RunEventSource(StrEnum):
    API = "api"
    WORKER = "worker"
    AGENT = "agent"
    BASTION = "bastion"
    OPERATOR = "operator"
    GRADER = "grader"
    SYSTEM = "system"


class ActorType(StrEnum):
    SYSTEM = "system"
    WORKER = "worker"
    AGENT = "agent"
    BASTION = "bastion"
    OPERATOR = "operator"
    GRADER = "grader"


class EnvironmentRef(AtlasModel):
    environment_id: str
    environment_name: str
    environment_version: str | None = None


class ScenarioRef(AtlasModel):
    scenario_id: str
    environment_id: str
    scenario_name: str
    scenario_seed: str


class TaskRef(AtlasModel):
    task_id: str
    scenario_id: str
    task_kind: str
    task_title: str


class RunStep(AtlasModel):
    step_id: str
    run_id: str
    step_index: int = Field(ge=0)
    title: str
    status: RunStepStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None


class ToolCall(AtlasModel):
    tool_call_id: str
    tool_name: str
    action: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: ToolCallStatus
    result: dict[str, Any] | None = None
    error_message: str | None = None


class PolicyDecision(AtlasModel):
    decision_id: str
    outcome: PolicyDecisionOutcome
    action_type: str
    rationale: str
    approval_request_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Artifact(AtlasModel):
    schema_version: int = Field(default=CURRENT_SCHEMA_VERSION, ge=1)
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
    size_bytes: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GradeResult(AtlasModel):
    grade_id: str | None = None
    outcome: GradeOutcome
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    summary: str
    rubric_version: str | None = None
    evidence_artifact_ids: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class Run(AtlasModel):
    run_id: str
    environment: EnvironmentRef
    scenario: ScenarioRef
    task: TaskRef
    status: RunStatus
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    current_step_index: int = Field(default=0, ge=0)
    active_agent_id: str | None = None
    grade_result: GradeResult | None = None


class EventPayloadModel(AtlasModel):
    schema_version: int = Field(default=CURRENT_SCHEMA_VERSION, ge=1)


class RunCreatedPayload(EventPayloadModel):
    event_type: Literal[RunEventType.RUN_CREATED]
    run: Run


class RunReadyPayload(EventPayloadModel):
    event_type: Literal[RunEventType.RUN_READY]
    run_id: str
    status: Literal[RunStatus.READY]


class RunStartedPayload(EventPayloadModel):
    event_type: Literal[RunEventType.RUN_STARTED]
    run_id: str
    status: Literal[RunStatus.RUNNING]
    started_at: datetime


class RunStepCreatedPayload(EventPayloadModel):
    event_type: Literal[RunEventType.RUN_STEP_CREATED]
    run_id: str
    step: RunStep


class ToolCallRecordedPayload(EventPayloadModel):
    event_type: Literal[RunEventType.TOOL_CALL_RECORDED]
    run_id: str
    step_id: str | None = None
    tool_call: ToolCall
    policy_decision: PolicyDecision | None = None


class ArtifactAttachedPayload(EventPayloadModel):
    event_type: Literal[RunEventType.ARTIFACT_ATTACHED]
    run_id: str
    step_id: str | None = None
    artifact: Artifact


class RunCompletedPayload(EventPayloadModel):
    event_type: Literal[RunEventType.RUN_COMPLETED]
    run_id: str
    final_status: Literal[
        RunStatus.SUCCEEDED,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    ]
    completed_at: datetime
    grade_result: GradeResult | None = None


RunEventPayload = Annotated[
    RunCreatedPayload
    | RunReadyPayload
    | RunStartedPayload
    | RunStepCreatedPayload
    | ToolCallRecordedPayload
    | ArtifactAttachedPayload
    | RunCompletedPayload,
    Field(discriminator="event_type"),
]


class RunEvent(AtlasModel):
    schema_version: int = Field(default=CURRENT_SCHEMA_VERSION, ge=1)
    event_id: str
    run_id: str
    sequence: int = Field(ge=0)
    occurred_at: datetime
    source: RunEventSource
    actor_type: ActorType
    correlation_id: str | None = None
    event_type: RunEventType
    payload: RunEventPayload

    @model_validator(mode="after")
    def validate_event_type_matches_payload(self) -> "RunEvent":
        if self.event_type != self.payload.event_type:
            raise ValueError("event_type must match payload.event_type")
        return self
