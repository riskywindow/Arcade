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
    | RunStepCreatedPayloadSchema
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


class ArtifactListResponse(ApiModel):
    run_id: str
    artifacts: list[ArtifactSchema]
