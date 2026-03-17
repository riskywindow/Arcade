"""Model gateway package."""

from atlas_core.package_info import PackageInfo
from model_gateway.contracts import (
    AgentConfig,
    ModelInvocation,
    ModelProvider,
    ModelResponse,
    ModelToolDefinition,
    RetryPolicy,
)
from model_gateway.fake_provider import FakeModelProvider
from model_gateway.gateway import ModelGateway

PACKAGE_INFO = PackageInfo(
    name="model-gateway",
    purpose="Model/provider abstraction boundary for runtime integration.",
    phase_boundary="Phase 4 adds provider-agnostic contracts and a deterministic fake provider only.",
)

__all__ = [
    "AgentConfig",
    "FakeModelProvider",
    "ModelGateway",
    "ModelInvocation",
    "ModelProvider",
    "ModelResponse",
    "ModelToolDefinition",
    "PACKAGE_INFO",
    "RetryPolicy",
]
