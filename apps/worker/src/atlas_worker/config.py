from __future__ import annotations

import os
from dataclasses import dataclass

from atlas_core.config import InfrastructureConfig, ServiceConfig
from model_gateway import AgentConfig, RetryPolicy


@dataclass(frozen=True)
class WorkerConfig:
    service: ServiceConfig
    infrastructure: InfrastructureConfig
    agent: AgentConfig
    artifact_storage_dir: str


def load_config() -> WorkerConfig:
    return WorkerConfig(
        service=ServiceConfig.from_env(
            prefix="ATLAS_WORKER",
            service_name="atlas-worker",
            default_port=8100,
        ),
        infrastructure=InfrastructureConfig.from_env(),
        agent=AgentConfig(
            provider=os.getenv("ATLAS_AGENT_PROVIDER", "fake"),
            model_name=os.getenv("ATLAS_AGENT_MODEL", "phase4-fake"),
            temperature=float(os.getenv("ATLAS_AGENT_TEMPERATURE", "0.0")),
            deterministic=os.getenv("ATLAS_AGENT_DETERMINISTIC", "true").lower() != "false",
            max_steps=int(os.getenv("ATLAS_AGENT_MAX_STEPS", "8")),
            retry_policy=RetryPolicy(
                max_attempts=int(os.getenv("ATLAS_AGENT_MAX_ATTEMPTS", "2")),
                retryable_error_kinds=_split_csv(
                    os.getenv(
                        "ATLAS_AGENT_RETRYABLE_ERROR_KINDS",
                        "model_error,retriable_tool_error",
                    )
                ),
            ),
            allowed_tool_names=_split_csv(os.getenv("ATLAS_AGENT_ALLOWED_TOOLS", "")),
        ),
        artifact_storage_dir=os.getenv("ATLAS_ARTIFACTS_DIR", "/tmp/atlas-artifacts"),
    )


def _split_csv(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())
