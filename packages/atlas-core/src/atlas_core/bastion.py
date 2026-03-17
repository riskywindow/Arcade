from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from atlas_core.domain import (
    ActorType,
    EnvironmentRef,
    PolicyDecision,
    PolicyDecisionOutcome,
    ScenarioRef,
    TaskRef,
)
from atlas_core.execution import ToolRequest, ToolResult
from atlas_core.tools import ToolExecutor, ToolSpec


class BastionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PolicyCategory(StrEnum):
    SAFE_READ = "safe_read"
    ROUTINE_MUTATION = "routine_mutation"
    SENSITIVE_MUTATION = "sensitive_mutation"
    FORBIDDEN_SHORTCUT = "forbidden_shortcut"
    SECRET_ACCESS = "secret_access"
    APPROVAL_GATED = "approval_gated"


class ResourceSensitivity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalRequestStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class SecretHandleKind(StrEnum):
    PASSWORD = "password"
    API_TOKEN = "api_token"
    SESSION_COOKIE = "session_cookie"
    OPAQUE_VALUE = "opaque_value"


class AuditEventKind(StrEnum):
    TOOL_REQUEST_RECEIVED = "tool_request_received"
    POLICY_EVALUATED = "policy_evaluated"
    TOOL_EXECUTION_COMPLETED = "tool_execution_completed"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_RESOLVED = "approval_resolved"
    SECRET_BROKERED = "secret_brokered"
    KILL_SWITCH_TRIGGERED = "kill_switch_triggered"


class SecretHandle(BastionModel):
    secret_id: str
    handle: str
    kind: SecretHandleKind
    scope: str
    redaction_hint: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApprovalRequestRef(BastionModel):
    approval_request_id: str
    run_id: str
    step_id: str | None = None
    status: ApprovalRequestStatus
    requested_action_type: str
    tool_name: str | None = None
    requested_arguments: dict[str, Any] = Field(default_factory=dict)
    requester_role: str = "helpdesk_agent"
    reason_code: str | None = None
    summary: str | None = None
    target_resource_type: str | None = None
    target_resource_id: str | None = None
    requested_at: datetime
    expires_at: datetime | None = None
    resolved_at: datetime | None = None
    resolution_summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditRecordEnvelope(BastionModel):
    audit_id: str
    run_id: str
    step_id: str | None = None
    request_id: str | None = None
    actor_type: ActorType
    event_kind: AuditEventKind
    occurred_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class BastionToolRequest(BastionModel):
    request_id: str
    run_id: str
    step_id: str
    turn_id: str | None = None
    agent_id: str | None = None
    environment: EnvironmentRef
    scenario: ScenarioRef
    task: TaskRef
    tool_request: ToolRequest
    tool_spec: ToolSpec
    requested_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PolicyEvaluationInput(BastionModel):
    request_id: str
    run_id: str
    step_id: str
    agent_id: str | None = None
    environment: EnvironmentRef
    scenario: ScenarioRef
    task: TaskRef
    tool_name: str
    action_type: str
    requester_role: str = "helpdesk_agent"
    target_resource_type: str | None = None
    target_resource_id: str | None = None
    policy_category_hint: PolicyCategory | None = None
    resource_sensitivity: ResourceSensitivity = ResourceSensitivity.LOW
    read_only: bool
    requires_browser: bool
    secret_access_requested: bool = False
    tool_tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)


class PolicyEvaluationResult(BastionModel):
    decision: PolicyDecision
    category: PolicyCategory
    reason_code: str
    enforcement_message: str | None = None
    audit_metadata: dict[str, Any] = Field(default_factory=dict)


class PolicyRuleMatch(BastionModel):
    scenario_ids: tuple[str, ...] = ()
    task_kinds: tuple[str, ...] = ()
    requester_roles: tuple[str, ...] = ()
    tool_names: tuple[str, ...] = ()
    action_types: tuple[str, ...] = ()
    target_resource_types: tuple[str, ...] = ()
    policy_categories: tuple[PolicyCategory, ...] = ()
    resource_sensitivities: tuple[ResourceSensitivity, ...] = ()
    read_only: bool | None = None
    requires_browser: bool | None = None
    secret_access_requested: bool | None = None
    tool_tags_all: tuple[str, ...] = ()


class PolicyRule(BastionModel):
    rule_id: str
    description: str
    priority: int = Field(default=100, ge=1, le=10_000)
    match: PolicyRuleMatch = Field(default_factory=PolicyRuleMatch)
    outcome: PolicyDecisionOutcome
    category: PolicyCategory
    rationale: str
    reason_code: str | None = None
    enforcement_message: str | None = None
    approval_action_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PolicyPack(BastionModel):
    pack_id: str
    version: str
    default_outcome: PolicyDecisionOutcome
    default_category: PolicyCategory
    default_rationale: str
    default_reason_code: str | None = None
    rules: tuple[PolicyRule, ...] = ()


class BastionToolResponse(BastionModel):
    request_id: str
    run_id: str
    step_id: str
    policy_evaluation: PolicyEvaluationResult
    tool_result: ToolResult | None = None
    approval_request: ApprovalRequestRef | None = None
    secret_handles: tuple[SecretHandle, ...] = ()
    audit_records: tuple[AuditRecordEnvelope, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_decision_shape(self) -> "BastionToolResponse":
        outcome = self.policy_evaluation.decision.outcome.value
        if outcome == "allow" and self.approval_request is not None:
            raise ValueError("allow responses must not include an approval_request")
        if outcome == "deny" and self.tool_result is not None:
            raise ValueError("deny responses must not include a tool_result")
        if outcome == "require_approval" and self.approval_request is None:
            raise ValueError("require_approval responses must include an approval_request")
        return self


@runtime_checkable
class BastionToolGateway(Protocol):
    def handle_tool_request(
        self,
        request: BastionToolRequest,
        *,
        executor: ToolExecutor | None = None,
    ) -> BastionToolResponse:
        """Evaluate and optionally execute a Bastion-mediated tool request."""


@runtime_checkable
class PolicyEvaluator(Protocol):
    def evaluate(self, policy_input: PolicyEvaluationInput) -> PolicyEvaluationResult:
        """Evaluate a tool request before any irreversible side effects occur."""


@runtime_checkable
class ApprovalStore(Protocol):
    def create(self, request: ApprovalRequestRef) -> ApprovalRequestRef:
        """Persist an approval request reference."""

    def get(self, approval_request_id: str) -> ApprovalRequestRef | None:
        """Load an approval request reference if it exists."""

    def upsert(self, request: ApprovalRequestRef) -> ApprovalRequestRef:
        """Persist an updated approval request reference."""


@runtime_checkable
class AuditRecorder(Protocol):
    def record(self, records: tuple[AuditRecordEnvelope, ...]) -> None:
        """Persist or forward Bastion audit records."""


@runtime_checkable
class SecretsBroker(Protocol):
    def resolve(self, handles: tuple[SecretHandle, ...]) -> dict[str, str]:
        """Resolve secret handles for execution without exposing raw values to the model."""
