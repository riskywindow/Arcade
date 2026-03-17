from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import Field, model_validator

from atlas_core.domain import (
    AtlasModel,
    EnvironmentRef,
    RunStatus,
    ScenarioRef,
    TaskRef,
)


class ToolResultOutcome(StrEnum):
    SUCCESS = "success"
    RETRIABLE_ERROR = "retriable_error"
    FATAL_ERROR = "fatal_error"
    INVALID_REQUEST = "invalid_request"


class TerminationReason(StrEnum):
    SUCCESS = "success"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVAL_DENIED = "approval_denied"
    MAX_STEPS_EXCEEDED = "max_steps_exceeded"
    INVALID_TOOL_REQUEST = "invalid_tool_request"
    REPEATED_FAILURE = "repeated_failure"
    MODEL_ERROR = "model_error"
    SCENARIO_UNRECOVERABLE = "scenario_unrecoverable"
    CANCELLED = "cancelled"


class ToolRequest(AtlasModel):
    request_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    turn_id: str | None = None
    requested_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolResult(AtlasModel):
    request_id: str
    tool_name: str
    outcome: ToolResultOutcome
    result: dict[str, Any] | None = None
    error_message: str | None = None
    artifact_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_outcome_fields(self) -> "ToolResult":
        if self.outcome == ToolResultOutcome.SUCCESS:
            if self.error_message is not None:
                raise ValueError("error_message must be omitted for successful tool results")
            return self

        if self.error_message is None:
            raise ValueError("error_message is required for non-successful tool results")
        return self


class AgentTurn(AtlasModel):
    turn_id: str
    run_id: str
    turn_index: int = Field(ge=1)
    summary: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    tool_request: ToolRequest | None = None
    tool_result: ToolResult | None = None
    final_output: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_turn_shape(self) -> "AgentTurn":
        if self.tool_result is not None and self.tool_request is None:
            raise ValueError("tool_result requires a matching tool_request")

        has_tool_path = self.tool_request is not None
        has_final_output = self.final_output is not None
        if has_tool_path == has_final_output:
            raise ValueError("exactly one of tool_request or final_output must be provided")
        return self


class ExecutionContext(AtlasModel):
    run_id: str
    agent_id: str | None = None
    environment: EnvironmentRef
    scenario: ScenarioRef
    task: TaskRef
    task_brief: str
    success_condition: str | None = None
    allowed_tool_names: tuple[str, ...]
    max_turns: int = Field(default=8, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunExecutionSummary(AtlasModel):
    run_id: str
    agent_id: str | None = None
    final_run_status: RunStatus
    termination_reason: TerminationReason
    turns_executed: int = Field(ge=0)
    steps_recorded: int = Field(ge=0)
    tool_calls_recorded: int = Field(ge=0)
    artifact_ids: tuple[str, ...] = ()
    final_output: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class AgentRunner(Protocol):
    def run(self, context: ExecutionContext) -> RunExecutionSummary:
        """Execute one agent run for the provided execution context."""
