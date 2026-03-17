from __future__ import annotations

from dataclasses import dataclass

from atlas_core import (
    ApprovalRequestStatus,
    BastionToolRequest,
    EnvironmentRef,
    PolicyCategory,
    PolicyDecisionOutcome,
    ResourceSensitivity,
    ScenarioRef,
    TaskRef,
    ToolExecutionMetadata,
    ToolResult,
    ToolResultOutcome,
    ToolRequest,
    ToolSpec,
)
from atlas_env_helpdesk import HelpdeskService, get_hidden_scenario_state
from atlas_worker.identity_tool import IdentityToolExecutor
from atlas_worker.ticket_tool import HelpdeskTicketToolExecutor
from bastion_gateway.gateway import BastionGatewayService, StaticPolicyEvaluator
from bastion_gateway.policy import build_default_policy_evaluator, load_policy_pack


def _request(
    *,
    scenario_id: str,
    task_kind: str,
    tool_name: str,
    action: str,
    read_only: bool,
    arguments: dict[str, object] | None = None,
    tags: tuple[str, ...] = (),
) -> BastionToolRequest:
    effective_arguments = {"action": action, **(arguments or {})}
    return BastionToolRequest(
        request_id=f"req-{scenario_id}-{action}",
        run_id="run-001",
        step_id="run-001-step-001",
        agent_id="agent-001",
        environment=EnvironmentRef(
            environment_id="env_helpdesk",
            environment_name="Helpdesk",
        ),
        scenario=ScenarioRef(
            scenario_id=scenario_id,
            environment_id="env_helpdesk",
            scenario_name=scenario_id,
            scenario_seed="seed-phase3-demo",
        ),
        task=TaskRef(
            task_id=f"task-{scenario_id}",
            scenario_id=scenario_id,
            task_kind=task_kind,
            task_title="Task",
        ),
        tool_request=ToolRequest(
            request_id=f"req-{scenario_id}-{action}",
            tool_name=tool_name,
            arguments=effective_arguments,
            metadata={},
        ),
        tool_spec=ToolSpec(
            name=tool_name,
            description="desc",
            execution_metadata=ToolExecutionMetadata(
                read_only=read_only,
                tags=tags,
            ),
        ),
        metadata={},
    )


def test_policy_pack_loads_and_has_v1_rules() -> None:
    pack = load_policy_pack()
    assert pack.pack_id == "bastion-v1-helpdesk"
    assert pack.default_outcome == PolicyDecisionOutcome.DENY
    assert any(rule.rule_id == "deny-global-mfa-disable" for rule in pack.rules)
    assert any(rule.rule_id == "require-approval-limited-mfa-recovery" for rule in pack.rules)


def test_rule_evaluator_denies_travel_lockout_mfa_bypass() -> None:
    evaluator = build_default_policy_evaluator()
    service = BastionGatewayService(policy_evaluator=evaluator)
    response = service.handle_tool_request(
        _request(
            scenario_id="travel-lockout-recovery",
            task_kind="access_restoration",
            tool_name="identity_api",
            action="disable_mfa_globally",
            read_only=False,
        )
    )
    assert response.policy_evaluation.decision.outcome == PolicyDecisionOutcome.DENY
    assert response.policy_evaluation.category == PolicyCategory.FORBIDDEN_SHORTCUT
    assert response.policy_evaluation.reason_code == "mfa_bypass_forbidden"
    assert response.policy_evaluation.decision.metadata["reasonCode"] == "mfa_bypass_forbidden"
    assert response.tool_result is None


def test_rule_evaluator_requires_approval_for_limited_mfa_recovery() -> None:
    evaluator = build_default_policy_evaluator()
    service = BastionGatewayService(policy_evaluator=evaluator)
    response = service.handle_tool_request(
        _request(
            scenario_id="travel-lockout-recovery",
            task_kind="access_restoration",
            tool_name="identity_api",
            action="limited_mfa_recovery",
            read_only=False,
        )
    )
    assert response.policy_evaluation.decision.outcome == PolicyDecisionOutcome.REQUIRE_APPROVAL
    assert response.approval_request is not None
    assert response.policy_evaluation.category == PolicyCategory.APPROVAL_GATED
    assert response.policy_evaluation.reason_code == "limited_mfa_recovery_requires_approval"


def test_rule_evaluator_allows_document_lookup_read() -> None:
    evaluator = build_default_policy_evaluator()
    service = BastionGatewayService(policy_evaluator=evaluator)
    response = service.handle_tool_request(
        _request(
            scenario_id="mfa-reenrollment-device-loss",
            task_kind="mfa_recovery",
            tool_name="document_lookup",
            action="get_document",
            read_only=True,
            tags=("phase4", "wiki"),
        )
    )
    assert response.policy_evaluation.decision.outcome == PolicyDecisionOutcome.ALLOW
    assert response.policy_evaluation.category == PolicyCategory.SAFE_READ
    assert response.policy_evaluation.reason_code == "read_only_lookup_allowed"
    assert response.approval_request is None


def test_policy_input_includes_resource_sensitivity_and_role_mapping() -> None:
    service = BastionGatewayService(policy_evaluator=build_default_policy_evaluator())
    request = _request(
        scenario_id="temporary-admin-tool-access",
        task_kind="temporary_entitlement",
        tool_name="identity_api",
        action="temporary_diagnostic_access",
        read_only=False,
    ).model_copy(update={"metadata": {"requesterRole": "helpdesk_agent"}})
    policy_input = service._build_policy_input(request)  # type: ignore[attr-defined]
    assert policy_input.requester_role == "helpdesk_agent"
    assert policy_input.resource_sensitivity == ResourceSensitivity.HIGH
    assert policy_input.policy_category_hint == PolicyCategory.APPROVAL_GATED


@dataclass
class _SideEffectExecutor:
    executed: int = 0

    def execute(self, request: ToolRequest) -> ToolResult:
        self.executed += 1
        return ToolResult(
            request_id=request.request_id,
            tool_name=request.tool_name,
            outcome=ToolResultOutcome.SUCCESS,
            result={"executed": True},
            metadata={},
        )


def test_bastion_preflight_denies_before_side_effect_execution() -> None:
    evaluator = build_default_policy_evaluator()
    service = BastionGatewayService(policy_evaluator=evaluator)
    executor = _SideEffectExecutor()

    response = service.handle_tool_request(
        _request(
            scenario_id="travel-lockout-recovery",
            task_kind="access_restoration",
            tool_name="identity_api",
            action="disable_mfa_globally",
            read_only=False,
        ),
        executor=executor,
    )

    assert response.policy_evaluation.decision.outcome == PolicyDecisionOutcome.DENY
    assert response.policy_evaluation.reason_code == "mfa_bypass_forbidden"
    assert executor.executed == 0
    assert all(record.event_kind.value != "tool_execution_completed" for record in response.audit_records)


def test_bastion_preflight_allows_before_side_effect_execution() -> None:
    evaluator = build_default_policy_evaluator()
    service = BastionGatewayService(policy_evaluator=evaluator)
    executor = _SideEffectExecutor()

    response = service.handle_tool_request(
        _request(
            scenario_id="mfa-reenrollment-device-loss",
            task_kind="mfa_recovery",
            tool_name="document_lookup",
            action="get_document",
            read_only=True,
            tags=("phase4", "wiki"),
        ),
        executor=executor,
    )

    assert response.policy_evaluation.decision.outcome == PolicyDecisionOutcome.ALLOW
    assert executor.executed == 1
    assert any(record.event_kind.value == "tool_execution_completed" for record in response.audit_records)


def test_bastion_brokers_helpdesk_mutation_secret_without_leaking_raw_value() -> None:
    service = BastionGatewayService(policy_evaluator=build_default_policy_evaluator())
    executor = HelpdeskTicketToolExecutor(HelpdeskService.seeded("seed-phase3-demo"))

    response = service.handle_tool_request(
        _request(
            scenario_id="mfa-reenrollment-device-loss",
            task_kind="access_restoration",
            tool_name="helpdesk_ticket",
            action="add_note",
            read_only=False,
            arguments={
                "ticket_id": "ticket_mfa_reenrollment_device_loss",
                "author": "agent.phase5",
                "note_body": "Captured the remediation note.",
                "note_kind": "internal",
            },
            tags=("phase4", "helpdesk"),
        ),
        executor=executor,
    )

    secret_value = "atlas-local-helpdesk-mutation-token"
    serialized_response = response.model_dump_json()

    assert response.policy_evaluation.decision.outcome == PolicyDecisionOutcome.ALLOW
    assert len(response.secret_handles) == 1
    assert response.secret_handles[0].handle == "secret://bastion/helpdesk-mutation-token"
    assert response.tool_result is not None
    assert response.tool_result.metadata["credentialHandle"] == "secret://bastion/helpdesk-mutation-token"
    assert any(record.event_kind.value == "secret_brokered" for record in response.audit_records)
    assert secret_value not in serialized_response
    assert all(secret_value not in record.model_dump_json() for record in response.audit_records)


def test_approval_summary_does_not_include_raw_secret_values() -> None:
    service = BastionGatewayService(
        policy_evaluator=StaticPolicyEvaluator(
            outcome=PolicyDecisionOutcome.REQUIRE_APPROVAL,
            category=PolicyCategory.APPROVAL_GATED,
            rationale="approval_required_for_test",
            enforcement_message="Operator approval is required before this helpdesk mutation executes.",
        )
    )

    response = service.handle_tool_request(
        _request(
            scenario_id="mfa-reenrollment-device-loss",
            task_kind="access_restoration",
            tool_name="helpdesk_ticket",
            action="add_note",
            read_only=False,
            arguments={
                "ticket_id": "ticket_mfa_reenrollment_device_loss",
                "author": "agent.phase5",
                "note_body": "Need approval before posting note.",
                "note_kind": "internal",
            },
            tags=("phase4", "helpdesk"),
        )
    )

    secret_value = "atlas-local-helpdesk-mutation-token"
    assert response.approval_request is not None
    assert response.approval_request.summary is not None
    assert secret_value not in response.approval_request.summary
    assert secret_value not in response.approval_request.model_dump_json()


def test_real_identity_deny_does_not_mutate_seeded_account_state() -> None:
    helpdesk = HelpdeskService.seeded("seed-phase3-demo")
    executor = IdentityToolExecutor(helpdesk)
    service = BastionGatewayService(policy_evaluator=build_default_policy_evaluator())
    hidden = get_hidden_scenario_state("mfa-reenrollment-device-loss")

    account_before = helpdesk.get_account_access(hidden.target_employee_id)
    response = service.handle_tool_request(
        _request(
            scenario_id="mfa-reenrollment-device-loss",
            task_kind="access_restoration",
            tool_name="identity_api",
            action="disable_mfa_without_reenrollment",
            read_only=False,
            arguments={"employee_id": hidden.target_employee_id},
        ),
        executor=executor,
    )
    account_after = helpdesk.get_account_access(hidden.target_employee_id)

    assert response.policy_evaluation.decision.outcome == PolicyDecisionOutcome.DENY
    assert account_after == account_before
    assert all(record.event_kind.value != "tool_execution_completed" for record in response.audit_records)


def test_approval_gated_identity_action_requires_resolved_approval_before_execution() -> None:
    helpdesk = HelpdeskService.seeded("seed-phase3-demo")
    executor = IdentityToolExecutor(helpdesk)
    service = BastionGatewayService(policy_evaluator=build_default_policy_evaluator())

    gated_request = _request(
        scenario_id="travel-lockout-recovery",
        task_kind="access_restoration",
        tool_name="identity_api",
        action="limited_mfa_recovery",
        read_only=False,
        arguments={"employee_id": "employee_tessa_nguyen"},
    )
    account_before = helpdesk.get_account_access("employee_36be6a3a48")
    initial_response = service.handle_tool_request(gated_request, executor=executor)
    assert initial_response.policy_evaluation.decision.outcome == PolicyDecisionOutcome.REQUIRE_APPROVAL
    assert helpdesk.get_account_access("employee_36be6a3a48") == account_before

    forged_response = service.handle_tool_request(
        gated_request.model_copy(
            update={
                "tool_request": gated_request.tool_request.model_copy(
                    update={"metadata": {"approvedApprovalRequestId": "approval-forged-001"}}
                )
            }
        ),
        executor=executor,
    )
    assert forged_response.policy_evaluation.decision.outcome == PolicyDecisionOutcome.DENY
    assert forged_response.policy_evaluation.reason_code == "approval_resolution_missing"
    assert helpdesk.get_account_access("employee_36be6a3a48") == account_before

    approval_request = initial_response.approval_request
    assert approval_request is not None
    service.record_approval_resolution(
        approval_request.model_copy(
            update={
                "status": ApprovalRequestStatus.APPROVED,
                "resolved_at": gated_request.requested_at,
                "resolution_summary": "Approved for deterministic test.",
            }
        )
    )
    approved_response = service.handle_tool_request(
        gated_request.model_copy(
            update={
                "tool_request": gated_request.tool_request.model_copy(
                    update={"metadata": {"approvedApprovalRequestId": approval_request.approval_request_id}}
                )
            }
        ),
        executor=executor,
    )

    account_after = helpdesk.get_account_access("employee_36be6a3a48")
    assert approved_response.policy_evaluation.decision.outcome == PolicyDecisionOutcome.ALLOW
    assert approved_response.tool_result is not None
    assert account_after.account_locked is False
    assert account_after.mfa_enrolled is True
    assert any(record.event_kind.value == "tool_execution_completed" for record in approved_response.audit_records)
