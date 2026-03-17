from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from atlas_core.bastion import SecretHandle

from pydantic import ConfigDict, Field

from atlas_core.domain import AtlasModel
from atlas_core.execution import ToolRequest, ToolResult
from atlas_core.sandbox import SandboxRunner


class ToolContractModel(AtlasModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ToolExecutionMetadata(ToolContractModel):
    read_only: bool = False
    idempotent: bool = False
    requires_browser: bool = False
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    tags: tuple[str, ...] = ()


class ToolSpec(ToolContractModel):
    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    result_schema: dict[str, Any] = Field(default_factory=dict)
    execution_metadata: ToolExecutionMetadata = Field(default_factory=ToolExecutionMetadata)


@runtime_checkable
class ToolExecutor(Protocol):
    def execute(self, request: ToolRequest) -> ToolResult:
        """Execute a tool request and return a normalized tool result."""


@runtime_checkable
class SecretAwareToolExecutor(Protocol):
    def execute_with_secrets(
        self,
        request: ToolRequest,
        *,
        resolved_secrets: dict[str, str],
        secret_handles: tuple[SecretHandle, ...],
    ) -> ToolResult:
        """Execute a tool request with Bastion-resolved secrets kept out of model-visible contracts."""


@runtime_checkable
class SandboxedToolExecutor(Protocol):
    def execute_in_sandbox(
        self,
        request: ToolRequest,
        *,
        sandbox_runner: SandboxRunner,
    ) -> ToolResult:
        """Execute a high-risk tool request through Bastion's sandbox wrapper."""
