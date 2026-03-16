from __future__ import annotations

from dataclasses import dataclass

from atlas_core.config import InfrastructureConfig, ServiceConfig


@dataclass(frozen=True)
class WorkerConfig:
    service: ServiceConfig
    infrastructure: InfrastructureConfig


def load_config() -> WorkerConfig:
    return WorkerConfig(
        service=ServiceConfig.from_env(
            prefix="ATLAS_WORKER",
            service_name="atlas-worker",
            default_port=8100,
        ),
        infrastructure=InfrastructureConfig.from_env(),
    )
