from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from atlas_core import (
    ActorType,
    ApprovalStore,
    ApprovalRequestRef,
    ApprovalRequestStatus,
    AuditEventKind,
    AuditRecordEnvelope,
    AuditRecorder,
    BastionToolGateway,
    BastionToolRequest,
    BastionToolResponse,
    PolicyCategory,
    PolicyDecision,
    PolicyDecisionOutcome,
    PolicyEvaluationInput,
    PolicyEvaluationResult,
    PolicyEvaluator,
    ResourceSensitivity,
    SandboxRunner,
    SandboxedToolExecutor,
    SecretAwareToolExecutor,
    SecretHandle,
    SecretHandleKind,
    SecretsBroker,
    ToolExecutor,
)
from bastion_gateway.policy import build_default_policy_evaluator
from bastion_gateway.sandbox import DockerSandboxRunner


class InMemoryApprovalStore:
    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequestRef] = {}

    def create(self, request: ApprovalRequestRef) -> ApprovalRequestRef:
        self._requests[request.approval_request_id] = request
        return request

    def get(self, approval_request_id: str) -> ApprovalRequestRef | None:
        return self._requests.get(approval_request_id)

    def upsert(self, request: ApprovalRequestRef) -> ApprovalRequestRef:
        self._requests[request.approval_request_id] = request
        return request


class NoopAuditRecorder:
    def record(self, records: tuple[AuditRecordEnvelope, ...]) -> None:
        del records


class LocalSecretsBroker:
    def __init__(self, *, values: dict[str, str] | None = None) -> None:
        self._values = values or {
            "helpdesk_mutation_token": "atlas-local-helpdesk-mutation-token",
        }

    def resolve(self, handles: tuple[SecretHandle, ...]) -> dict[str, str]:
        resolved: dict[str, str] = {}
        for handle in handles:
            value = self._values.get(handle.secret_id)
            if value is None:
                raise ValueError(f"secret {handle.secret_id} is not configured")
            resolved[handle.handle] = value
        return resolved


class StaticPolicyEvaluator:
    def __init__(
        self,
        *,
        outcome: PolicyDecisionOutcome = PolicyDecisionOutcome.ALLOW,
        category: PolicyCategory = PolicyCategory.SAFE_READ,
        rationale: str = "phase5_skeleton_default",
        enforcement_message: str | None = None,
    ) -> None:
        self._outcome = outcome
        self._category = category
        self._rationale = rationale
        self._enforcement_message = enforcement_message

    def evaluate(self, policy_input: PolicyEvaluationInput) -> PolicyEvaluationResult:
        return PolicyEvaluationResult(
            decision=PolicyDecision(
                decision_id=f"policy-{policy_input.request_id}",
                outcome=self._outcome,
                action_type=policy_input.action_type,
                rationale=self._rationale,
                metadata={
                    "toolName": policy_input.tool_name,
                    "readOnly": policy_input.read_only,
                    "requiresBrowser": policy_input.requires_browser,
                    "reasonCode": self._rationale,
                    "toolTags": list(policy_input.tool_tags),
                },
            ),
            category=self._category,
            reason_code=self._rationale,
            enforcement_message=self._enforcement_message,
            audit_metadata={"skeleton": True, "reasonCode": self._rationale},
        )


class BastionGatewayService(BastionToolGateway):
    def __init__(
        self,
        *,
        policy_evaluator: PolicyEvaluator | None = None,
        approval_store: ApprovalStore | None = None,
        audit_recorder: AuditRecorder | None = None,
        secrets_broker: SecretsBroker | None = None,
        sandbox_runner: SandboxRunner | None = None,
    ) -> None:
        self._policy_evaluator = policy_evaluator or build_default_policy_evaluator()
        self._approval_store = approval_store or InMemoryApprovalStore()
        self._audit_recorder = audit_recorder or NoopAuditRecorder()
        self._secrets_broker = secrets_broker or LocalSecretsBroker()
        self._sandbox_runner = sandbox_runner or DockerSandboxRunner()

    def record_approval_resolution(self, approval_request: ApprovalRequestRef) -> ApprovalRequestRef:
        return self._approval_store.upsert(approval_request)

    def handle_tool_request(
        self,
        request: BastionToolRequest,
        *,
        executor: ToolExecutor | None = None,
    ) -> BastionToolResponse:
        now = request.requested_at or datetime.now(tz=UTC)
        policy_input = self._build_policy_input(request)
        policy_result = self._policy_evaluator.evaluate(policy_input)
        audit_records = [self._received_record(request=request, occurred_at=now)]
        audit_records.append(
            AuditRecordEnvelope(
                audit_id=f"audit-policy-{request.request_id}",
                run_id=request.run_id,
                step_id=request.step_id,
                request_id=request.request_id,
                actor_type=ActorType.BASTION,
                event_kind=AuditEventKind.POLICY_EVALUATED,
                occurred_at=now,
                payload={
                    "decisionId": policy_result.decision.decision_id,
                    "outcome": policy_result.decision.outcome.value,
                    "category": policy_result.category.value,
                    "reasonCode": policy_result.reason_code,
                    "matchedRuleId": policy_result.audit_metadata.get("matchedRuleId"),
                },
            )
        )

        approved_approval_request_id = request.tool_request.metadata.get("approvedApprovalRequestId")
        if isinstance(approved_approval_request_id, str) and approved_approval_request_id:
            recorded_approval = self._approval_store.get(approved_approval_request_id)
            if (
                recorded_approval is None
                or recorded_approval.status != ApprovalRequestStatus.APPROVED
                or recorded_approval.run_id != request.run_id
                or recorded_approval.requested_action_type != policy_input.action_type
            ):
                denial_policy = PolicyEvaluationResult(
                    decision=PolicyDecision(
                        decision_id=f"policy-{request.request_id}-approval-not-resolved",
                        outcome=PolicyDecisionOutcome.DENY,
                        action_type=policy_input.action_type,
                        rationale="approval_resolution_missing",
                        metadata={
                            "toolName": policy_input.tool_name,
                            "reasonCode": "approval_resolution_missing",
                            "approvedApprovalRequestId": approved_approval_request_id,
                        },
                    ),
                    category=PolicyCategory.APPROVAL_GATED,
                    reason_code="approval_resolution_missing",
                    enforcement_message="Approved execution is blocked until Bastion has a resolved approval record.",
                    audit_metadata={
                        "reasonCode": "approval_resolution_missing",
                        "approvedApprovalRequestId": approved_approval_request_id,
                    },
                )
                denial_audit_records = [
                    audit_records[0],
                    AuditRecordEnvelope(
                        audit_id=f"audit-policy-{request.request_id}",
                        run_id=request.run_id,
                        step_id=request.step_id,
                        request_id=request.request_id,
                        actor_type=ActorType.BASTION,
                        event_kind=AuditEventKind.POLICY_EVALUATED,
                        occurred_at=now,
                        payload={
                            "decisionId": denial_policy.decision.decision_id,
                            "outcome": denial_policy.decision.outcome.value,
                            "category": denial_policy.category.value,
                            "reasonCode": denial_policy.reason_code,
                            "matchedRuleId": denial_policy.audit_metadata.get("matchedRuleId"),
                        },
                    ),
                ]
                response = BastionToolResponse(
                    request_id=request.request_id,
                    run_id=request.run_id,
                    step_id=request.step_id,
                    policy_evaluation=denial_policy,
                    audit_records=tuple(denial_audit_records),
                    metadata={"approvalResolutionMissing": True},
                )
                self._audit_recorder.record(response.audit_records)
                return response
            policy_result = policy_result.model_copy(
                update={
                    "decision": policy_result.decision.model_copy(
                        update={
                            "outcome": PolicyDecisionOutcome.ALLOW,
                            "approval_request_id": approved_approval_request_id,
                            "metadata": {
                                **policy_result.decision.metadata,
                                "reasonCode": "approved_action_execution",
                                "approvedApprovalRequestId": approved_approval_request_id,
                            },
                        }
                    ),
                    "category": PolicyCategory.APPROVAL_GATED,
                    "reason_code": "approved_action_execution",
                    "enforcement_message": None,
                    "audit_metadata": {
                        **policy_result.audit_metadata,
                        "reasonCode": "approved_action_execution",
                        "approvedApprovalRequestId": approved_approval_request_id,
                    },
                }
            )
            audit_records.append(
                AuditRecordEnvelope(
                    audit_id=f"audit-approved-execution-{request.request_id}",
                    run_id=request.run_id,
                    step_id=request.step_id,
                    request_id=request.request_id,
                    actor_type=ActorType.BASTION,
                    event_kind=AuditEventKind.APPROVAL_RESOLVED,
                    occurred_at=now,
                    payload={"approvalRequestId": approved_approval_request_id, "phase": "executing"},
                )
            )

        if policy_result.decision.outcome == PolicyDecisionOutcome.DENY:
            response = BastionToolResponse(
                request_id=request.request_id,
                run_id=request.run_id,
                step_id=request.step_id,
                policy_evaluation=policy_result,
                audit_records=tuple(audit_records),
                metadata={"skeleton": True},
            )
            self._audit_recorder.record(response.audit_records)
            return response

        if policy_result.decision.outcome == PolicyDecisionOutcome.REQUIRE_APPROVAL:
            approval_request = self._approval_store.create(
                ApprovalRequestRef(
                    approval_request_id=f"approval-{request.request_id}",
                    run_id=request.run_id,
                    step_id=request.step_id,
                    status=ApprovalRequestStatus.PENDING,
                    requested_action_type=policy_input.action_type,
                    tool_name=request.tool_request.tool_name,
                    requested_arguments=request.tool_request.arguments,
                    requester_role=policy_input.requester_role,
                    reason_code=policy_result.reason_code,
                    summary=policy_result.enforcement_message,
                    target_resource_type=policy_input.target_resource_type,
                    target_resource_id=policy_input.target_resource_id,
                    requested_at=now,
                    metadata={"skeleton": True},
                )
            )
            audit_records.append(
                AuditRecordEnvelope(
                    audit_id=f"audit-approval-{request.request_id}",
                    run_id=request.run_id,
                    step_id=request.step_id,
                    request_id=request.request_id,
                    actor_type=ActorType.BASTION,
                    event_kind=AuditEventKind.APPROVAL_REQUESTED,
                    occurred_at=now,
                    payload={"approvalRequestId": approval_request.approval_request_id},
                )
            )
            response = BastionToolResponse(
                request_id=request.request_id,
                run_id=request.run_id,
                step_id=request.step_id,
                policy_evaluation=policy_result.model_copy(
                    update={
                        "decision": policy_result.decision.model_copy(
                            update={"approval_request_id": approval_request.approval_request_id}
                        )
                    }
                ),
                approval_request=approval_request,
                audit_records=tuple(audit_records),
                metadata={"skeleton": True},
            )
            self._audit_recorder.record(response.audit_records)
            return response

        secret_handles = self._secret_handles_for_request(request)
        resolved_secrets: dict[str, str] = {}
        if secret_handles:
            resolved_secrets = self._secrets_broker.resolve(secret_handles)
            audit_records.append(
                AuditRecordEnvelope(
                    audit_id=f"audit-secrets-{request.request_id}",
                    run_id=request.run_id,
                    step_id=request.step_id,
                    request_id=request.request_id,
                    actor_type=ActorType.BASTION,
                    event_kind=AuditEventKind.SECRET_BROKERED,
                    occurred_at=now,
                    payload={
                        "secretHandles": [handle.handle for handle in secret_handles],
                        "secretKinds": [handle.kind.value for handle in secret_handles],
                    },
                )
            )
        tool_result = None
        sandboxed_execution = False
        if executor is not None:
            if isinstance(executor, SandboxedToolExecutor):
                sandboxed_execution = True
                tool_result = executor.execute_in_sandbox(
                    request.tool_request,
                    sandbox_runner=self._sandbox_runner,
                )
            elif secret_handles and isinstance(executor, SecretAwareToolExecutor):
                tool_result = executor.execute_with_secrets(
                    request.tool_request,
                    resolved_secrets=resolved_secrets,
                    secret_handles=secret_handles,
                )
            else:
                tool_result = executor.execute(request.tool_request)
        audit_records.append(
            AuditRecordEnvelope(
                audit_id=f"audit-execution-{request.request_id}",
                run_id=request.run_id,
                step_id=request.step_id,
                request_id=request.request_id,
                actor_type=ActorType.BASTION,
                event_kind=AuditEventKind.TOOL_EXECUTION_COMPLETED,
                occurred_at=now,
                payload={
                    "executed": executor is not None,
                    "sandboxed": sandboxed_execution,
                    "toolName": request.tool_request.tool_name,
                    "outcome": tool_result.outcome.value if tool_result is not None else None,
                },
            )
        )
        response = BastionToolResponse(
            request_id=request.request_id,
            run_id=request.run_id,
            step_id=request.step_id,
            policy_evaluation=policy_result,
            tool_result=tool_result,
            secret_handles=secret_handles,
            audit_records=tuple(audit_records),
            metadata={"skeleton": True, "executed": executor is not None},
        )
        self._audit_recorder.record(response.audit_records)
        return response

    def _build_policy_input(self, request: BastionToolRequest) -> PolicyEvaluationInput:
        action_type = str(request.tool_request.arguments.get("action", "invoke"))
        target_resource_id = self._target_resource_id(request.tool_request.arguments)
        read_only = self._is_read_only_request(request)
        return PolicyEvaluationInput(
            request_id=request.request_id,
            run_id=request.run_id,
            step_id=request.step_id,
            agent_id=request.agent_id,
            environment=request.environment,
            scenario=request.scenario,
            task=request.task,
            tool_name=request.tool_request.tool_name,
            action_type=action_type,
            requester_role=str(request.metadata.get("requesterRole", "helpdesk_agent")),
            target_resource_type=self._target_resource_type(request.tool_request.tool_name),
            target_resource_id=target_resource_id,
            policy_category_hint=self._policy_category_hint(request),
            resource_sensitivity=self._resource_sensitivity(request),
            read_only=read_only,
            requires_browser=request.tool_spec.execution_metadata.requires_browser,
            secret_access_requested=False,
            tool_tags=request.tool_spec.execution_metadata.tags,
            metadata={
                **request.metadata,
                "policyPackId": "bastion-v1-helpdesk",
            },
        )

    def _received_record(
        self,
        *,
        request: BastionToolRequest,
        occurred_at: datetime,
    ) -> AuditRecordEnvelope:
        return AuditRecordEnvelope(
            audit_id=f"audit-received-{request.request_id}",
            run_id=request.run_id,
            step_id=request.step_id,
            request_id=request.request_id,
            actor_type=ActorType.BASTION,
            event_kind=AuditEventKind.TOOL_REQUEST_RECEIVED,
            occurred_at=occurred_at,
            payload={
                "toolName": request.tool_request.tool_name,
                "actionType": request.tool_request.arguments.get("action"),
            },
        )

    @staticmethod
    def _target_resource_type(tool_name: str) -> str:
        if tool_name == "helpdesk_ticket":
            return "ticket"
        if tool_name == "identity_api":
            return "account_access"
        if tool_name == "directory_lookup":
            return "employee"
        if tool_name == "document_lookup":
            return "document"
        if tool_name == "browser":
            return "browser_surface"
        return "tool_resource"

    @staticmethod
    def _policy_category_hint(request: BastionToolRequest) -> PolicyCategory:
        action_type = str(request.tool_request.arguments.get("action", "invoke"))
        if BastionGatewayService._is_read_only_request(request):
            return PolicyCategory.SAFE_READ
        if action_type in {
            "disable_mfa_globally",
            "disable_mfa_without_reenrollment",
            "grant_standing_admin",
            "grant_finance_admin_bundle",
            "disable_account_immediately",
        }:
            return PolicyCategory.FORBIDDEN_SHORTCUT
        if action_type in {
            "limited_mfa_recovery",
            "finance_drive_access",
            "temporary_diagnostic_access",
        }:
            return PolicyCategory.APPROVAL_GATED
        return PolicyCategory.ROUTINE_MUTATION

    @staticmethod
    def _resource_sensitivity(request: BastionToolRequest) -> ResourceSensitivity:
        action_type = str(request.tool_request.arguments.get("action", "invoke"))
        if BastionGatewayService._is_read_only_request(request):
            return ResourceSensitivity.LOW
        if action_type in {
            "disable_mfa_globally",
            "disable_mfa_without_reenrollment",
            "grant_standing_admin",
            "grant_finance_admin_bundle",
            "disable_account_immediately",
        }:
            return ResourceSensitivity.CRITICAL
        if action_type in {
            "limited_mfa_recovery",
            "finance_drive_access",
            "temporary_diagnostic_access",
        }:
            return ResourceSensitivity.HIGH
        if request.tool_request.tool_name in {"helpdesk_ticket", "browser"}:
            return ResourceSensitivity.MEDIUM
        return ResourceSensitivity.HIGH

    @staticmethod
    def _target_resource_id(arguments: dict[str, Any]) -> str | None:
        for key in ("ticket_id", "employee_id", "slug", "target"):
            value = arguments.get(key)
            if isinstance(value, str) and value:
                return value
        return None

    @staticmethod
    def _is_read_only_request(request: BastionToolRequest) -> bool:
        if request.tool_spec.execution_metadata.read_only:
            return True
        action_type = str(request.tool_request.arguments.get("action", "invoke"))
        if request.tool_request.tool_name == "helpdesk_ticket" and action_type in {
            "list_tickets",
            "get_ticket",
        }:
            return True
        if request.tool_request.tool_name == "identity_api" and action_type == "get_account_access":
            return True
        return False

    @staticmethod
    def _secret_handles_for_request(request: BastionToolRequest) -> tuple[SecretHandle, ...]:
        action_type = str(request.tool_request.arguments.get("action", "invoke"))
        if request.tool_request.tool_name == "helpdesk_ticket" and action_type in {
            "add_note",
            "assign_ticket",
            "update_status",
        }:
            return (
                SecretHandle(
                    secret_id="helpdesk_mutation_token",
                    handle="secret://bastion/helpdesk-mutation-token",
                    kind=SecretHandleKind.API_TOKEN,
                    scope="helpdesk_ticket.mutation",
                    redaction_hint="helpdesk mutation token",
                    metadata={"toolName": request.tool_request.tool_name},
                ),
            )
        return ()


def build_bastion_gateway_service() -> BastionGatewayService:
    return BastionGatewayService()
