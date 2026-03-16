from __future__ import annotations

from dataclasses import dataclass

from atlas_core.config import InfrastructureConfig, ServiceConfig


@dataclass(frozen=True)
class ApiConfig:
    service: ServiceConfig
    infrastructure: InfrastructureConfig


def load_config() -> ApiConfig:
    return ApiConfig(
        service=ServiceConfig.from_env(
            prefix="ATLAS_API",
            service_name="atlas-api",
            default_port=8000,
        ),
        infrastructure=InfrastructureConfig.from_env(),
    )
