"""Bastion gateway service scaffolding."""

from bastion_gateway.contracts import (
    ApprovalRequestRef,
    ApprovalRequestStatus,
    AuditEventKind,
    AuditRecordEnvelope,
    BastionToolRequest,
    BastionToolResponse,
    PolicyCategory,
    PolicyPack,
    PolicyEvaluationInput,
    PolicyEvaluationResult,
    PolicyRule,
    PolicyRuleMatch,
    ResourceSensitivity,
    SecretHandle,
    SecretHandleKind,
)
from bastion_gateway.gateway import (
    BastionGatewayService,
    InMemoryApprovalStore,
    LocalSecretsBroker,
    NoopAuditRecorder,
    StaticPolicyEvaluator,
    build_bastion_gateway_service,
)
from bastion_gateway.policy import RuleBasedPolicyEvaluator, build_default_policy_evaluator, load_policy_pack
from bastion_gateway.sandbox import DockerSandboxRunner

__all__ = [
    "ApprovalRequestRef",
    "ApprovalRequestStatus",
    "AuditEventKind",
    "AuditRecordEnvelope",
    "BastionGatewayService",
    "BastionToolRequest",
    "BastionToolResponse",
    "InMemoryApprovalStore",
    "LocalSecretsBroker",
    "NoopAuditRecorder",
    "PolicyCategory",
    "PolicyPack",
    "PolicyEvaluationInput",
    "PolicyEvaluationResult",
    "PolicyRule",
    "PolicyRuleMatch",
    "ResourceSensitivity",
    "RuleBasedPolicyEvaluator",
    "SecretHandle",
    "SecretHandleKind",
    "StaticPolicyEvaluator",
    "build_default_policy_evaluator",
    "build_bastion_gateway_service",
    "DockerSandboxRunner",
    "load_policy_pack",
]
