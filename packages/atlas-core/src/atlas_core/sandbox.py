from __future__ import annotations

from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import Field

from atlas_core.domain import AtlasModel


class SandboxMode(StrEnum):
    DOCKER = "docker"


class SandboxExecutionRequest(AtlasModel):
    command: tuple[str, ...] = Field(min_length=1)
    image: str
    timeout_seconds: int = Field(default=10, ge=1, le=120)
    working_directory: str = "/workspace"
    read_only_root: bool = True
    network_disabled: bool = True
    environment: dict[str, str] = Field(default_factory=dict)
    mounts: tuple[str, ...] = ()
    metadata: dict[str, str] = Field(default_factory=dict)


class SandboxExecutionResult(AtlasModel):
    mode: SandboxMode
    command: tuple[str, ...]
    image: str
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
    metadata: dict[str, str] = Field(default_factory=dict)


@runtime_checkable
class SandboxRunner(Protocol):
    def run(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        """Execute one allowlisted command in an isolated sandbox."""
