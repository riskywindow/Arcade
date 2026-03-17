from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from atlas_core import AgentTurn, ExecutionContext, ToolRequest


class GatewayModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RetryPolicy(GatewayModel):
    max_attempts: int = Field(default=2, ge=1, le=5)
    retryable_error_kinds: tuple[str, ...] = ("model_error", "retriable_tool_error")


class AgentConfig(GatewayModel):
    provider: str = "fake"
    model_name: str
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    deterministic: bool = True
    max_steps: int = Field(default=8, ge=1, le=25)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    allowed_tool_names: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_determinism(self) -> "AgentConfig":
        if self.deterministic and self.temperature != 0.0:
            raise ValueError("deterministic agent configs must use temperature 0.0")
        return self


class ModelToolDefinition(GatewayModel):
    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelInvocation(GatewayModel):
    context: ExecutionContext
    agent_config: AgentConfig
    available_tools: tuple[ModelToolDefinition, ...] = ()
    turn_history: tuple[AgentTurn, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelResponse(GatewayModel):
    tool_request: ToolRequest | None = None
    final_output: str | None = None
    raw_output: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_response_shape(self) -> "ModelResponse":
        has_tool_request = self.tool_request is not None
        has_final_output = self.final_output is not None
        if has_tool_request == has_final_output:
            raise ValueError("exactly one of tool_request or final_output must be provided")
        return self


@runtime_checkable
class ModelProvider(Protocol):
    def generate(self, invocation: ModelInvocation) -> ModelResponse:
        """Produce the next model response for a single invocation."""
