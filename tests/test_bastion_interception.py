from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from atlas_core import (
    ActorType,
    ApprovalRequestedPayload,
    ApprovalRequestRef,
    ApprovalRequestStatus,
    AuditRecordEnvelope,
    AuditRecordedPayload,
    AuditEventKind,
    Artifact,
    BastionToolRequest,
    BastionToolResponse,
    PolicyCategory,
    PolicyDecision,
    PolicyDecisionOutcome,
    PolicyEvaluationResult,
    Run,
    RunCompletedPayload,
    RunEvent,
    RunEventSource,
    RunEventType,
    RunResumedPayload,
    RunStopRequestedPayload,
    RunStartedPayload,
    RunStatus,
    RunStepCreatedPayload,
    RunWaitingApprovalPayload,
    ToolRequest,
    ToolCallRecordedPayload,
)
from atlas_env_helpdesk import HelpdeskService
from atlas_worker.agent_execution import SeededAgentRunSpec, execute_seeded_agent_run
from browser_runner import BrowserAction, BrowserCommand, BrowserObservation, BrowserScreenshot
from model_gateway import AgentConfig, FakeModelProvider, ModelGateway, ModelResponse, RetryPolicy


class _FakeBrowserRunner:
    def __init__(self) -> None:
        self._current_url = "http://127.0.0.1:3000/internal/helpdesk"
        self._title = "Helpdesk"

    def run(self, command: BrowserCommand) -> BrowserObservation:
        if command.action == BrowserAction.OPEN and command.target:
            self._current_url = f"http://127.0.0.1:3000{command.target}"
            self._title = "Internal Helpdesk"
        return BrowserObservation(
            current_url=self._current_url,
            title=self._title,
            page_summary="Helpdesk Queue",
            extracted_text="Helpdesk Queue and seeded MFA ticket",
            visible_test_ids=("nav-link-helpdesk", "ticket-queue-table"),
        )

    def capture_screenshot(self, label: str | None = None) -> BrowserScreenshot:
        return BrowserScreenshot(
            current_url=self._current_url,
            title=self._title,
            screenshot_bytes=b"\x89PNG\r\nphase5-interception",
            default_filename=f"{label or 'browser'}.png",
        )

    def close(self) -> None:
        return None


@dataclass
class _MemoryRunService:
    runs: dict[str, Run] = field(default_factory=dict)
    events: dict[str, list[RunEvent]] = field(default_factory=dict)
    artifacts: dict[str, list[Artifact]] = field(default_factory=dict)

    def create_run(self, run: Run) -> Run:
        self.runs[run.run_id] = run
        self.events.setdefault(run.run_id, [])
        self.artifacts.setdefault(run.run_id, [])
        return run

    def get_run(self, run_id: str) -> Run:
        return self.runs[run_id]

    def next_event_sequence(self, run_id: str) -> int:
        return len(self.events[run_id])

    def append_run_event(self, event: RunEvent) -> RunEvent:
        self.events[event.run_id].append(event)
        run = self.runs[event.run_id]
        if event.event_type == RunEventType.RUN_READY:
            run = run.model_copy(update={"status": RunStatus.READY, "updated_at": event.occurred_at})
        elif event.event_type == RunEventType.RUN_STARTED:
            started_payload = cast(RunStartedPayload, event.payload)
            run = run.model_copy(
                update={
                    "status": RunStatus.RUNNING,
                    "started_at": started_payload.started_at,
                    "updated_at": event.occurred_at,
                }
            )
        elif event.event_type == RunEventType.RUN_WAITING_APPROVAL:
            waiting_payload = cast(RunWaitingApprovalPayload, event.payload)
            run = run.model_copy(
                update={
                    "status": waiting_payload.status,
                    "updated_at": event.occurred_at,
                }
            )
        elif event.event_type == RunEventType.RUN_RESUMED:
            resumed_payload = cast(RunResumedPayload, event.payload)
            run = run.model_copy(
                update={
                    "status": resumed_payload.status,
                    "updated_at": event.occurred_at,
                }
            )
        elif event.event_type == RunEventType.RUN_STEP_CREATED:
            step_payload = cast(RunStepCreatedPayload, event.payload)
            run = run.model_copy(
                update={
                    "current_step_index": step_payload.step.step_index,
                    "updated_at": event.occurred_at,
                }
            )
        elif event.event_type == RunEventType.RUN_COMPLETED:
            completed_payload = cast(RunCompletedPayload, event.payload)
            run = run.model_copy(
                update={
                    "status": completed_payload.final_status,
                    "completed_at": completed_payload.completed_at,
                    "updated_at": event.occurred_at,
                    "grade_result": completed_payload.grade_result,
                }
            )
        self.runs[event.run_id] = run
        return event

    def attach_artifact(self, *, run_id: str, artifact: Artifact, step_id: str | None = None) -> Artifact:
        attached = artifact.model_copy(update={"run_id": run_id, "step_id": step_id or artifact.step_id})
        self.artifacts[run_id].append(attached)
        return attached

    def list_run_events(self, run_id: str) -> list[RunEvent]:
        return list(self.events[run_id])

    def list_run_artifacts(self, run_id: str) -> list[Artifact]:
        return list(self.artifacts[run_id])


class _RecordingBastionGateway:
    def __init__(self) -> None:
        self.requests: list[BastionToolRequest] = []

    def handle_tool_request(
        self,
        request: BastionToolRequest,
        *,
        executor=None,
    ) -> BastionToolResponse:
        self.requests.append(request)
        assert executor is not None
        tool_result = executor.execute(request.tool_request)
        return BastionToolResponse(
            request_id=request.request_id,
            run_id=request.run_id,
            step_id=request.step_id,
            policy_evaluation=PolicyEvaluationResult(
                decision=PolicyDecision(
                    decision_id=f"decision-{request.request_id}",
                    outcome=PolicyDecisionOutcome.ALLOW,
                    action_type=str(request.tool_request.arguments.get("action", request.tool_request.tool_name)),
                    rationale="test_allow",
                    metadata={
                        "toolName": request.tool_request.tool_name,
                        "reasonCode": "test_allow",
                    },
                ),
                category=PolicyCategory.SAFE_READ,
                reason_code="test_allow",
                audit_metadata={"test": True, "reasonCode": "test_allow"},
            ),
            tool_result=tool_result,
            audit_records=(
                AuditRecordEnvelope(
                    audit_id=f"audit-{request.request_id}",
                    run_id=request.run_id,
                    step_id=request.step_id,
                    request_id=request.request_id,
                    actor_type=ActorType.BASTION,
                    event_kind=AuditEventKind.POLICY_EVALUATED,
                    occurred_at=cast(datetime, request.requested_at),
                    payload={"test": True},
                ),
            ),
            metadata={"test": True},
        )


class _ApprovalBastionGateway:
    def __init__(self) -> None:
        self.requests: list[BastionToolRequest] = []

    def handle_tool_request(
        self,
        request: BastionToolRequest,
        *,
        executor=None,
    ) -> BastionToolResponse:
        del executor
        self.requests.append(request)
        return BastionToolResponse(
            request_id=request.request_id,
            run_id=request.run_id,
            step_id=request.step_id,
            policy_evaluation=PolicyEvaluationResult(
                decision=PolicyDecision(
                    decision_id=f"decision-{request.request_id}",
                    outcome=PolicyDecisionOutcome.REQUIRE_APPROVAL,
                    action_type="temporary_diagnostic_access",
                    rationale="approval_required",
                    approval_request_id=f"approval-{request.request_id}",
                    metadata={
                        "toolName": request.tool_request.tool_name,
                        "reasonCode": "approval_required",
                    },
                ),
                category=PolicyCategory.APPROVAL_GATED,
                reason_code="approval_required",
                enforcement_message="Approval required before execution.",
                audit_metadata={"test": True, "reasonCode": "approval_required"},
            ),
            approval_request=ApprovalRequestRef(
                approval_request_id=f"approval-{request.request_id}",
                run_id=request.run_id,
                step_id=request.step_id,
                status=ApprovalRequestStatus.PENDING,
                requested_action_type="temporary_diagnostic_access",
                requested_at=cast(datetime, request.requested_at),
                metadata={"test": True},
            ),
            audit_records=(),
            metadata={"test": True},
        )


def _single_tool_agent_config(tool_name: str) -> AgentConfig:
    return AgentConfig(
        provider="fake",
        model_name="phase5-fake",
        deterministic=True,
        temperature=0.0,
        max_steps=2,
        retry_policy=RetryPolicy(max_attempts=1),
        allowed_tool_names=(tool_name,),
    )


def test_worker_routes_tool_execution_through_bastion_and_records_policy_decision(tmp_path: Path) -> None:
    run_service = _MemoryRunService()
    helpdesk_service = HelpdeskService.seeded("seed-phase3-demo")
    bastion_gateway = _RecordingBastionGateway()
    model_gateway = ModelGateway(
        FakeModelProvider(
            scripted_responses=(
                ModelResponse(
                    tool_request=ToolRequest(
                        request_id="toolreq-doc-001",
                        tool_name="document_lookup",
                        arguments={"action": "get_document", "slug": "mfa-device-loss-playbook"},
                    ),
                    metadata={"summary": "Read the MFA SOP"},
                ),
                ModelResponse(
                    final_output="Document reviewed.",
                    metadata={"summary": "Finish the run"},
                ),
            )
        )
    )

    result = execute_seeded_agent_run(
        cast(Any, run_service),
        spec=SeededAgentRunSpec(run_id="bastion-intercept-001"),
        agent_config=_single_tool_agent_config("document_lookup"),
        model_gateway=model_gateway,
        bastion_gateway=bastion_gateway,
        helpdesk_service=helpdesk_service,
        browser_runner=_FakeBrowserRunner(),
        artifact_storage_dir=str(tmp_path / "artifacts"),
    )

    assert result.event_count > 0
    assert len(bastion_gateway.requests) == 1
    assert bastion_gateway.requests[0].tool_request.tool_name == "document_lookup"

    tool_event = next(
        event
        for event in run_service.list_run_events(result.run_id)
        if event.event_type.value == "tool_call.recorded"
    )
    payload = cast(ToolCallRecordedPayload, tool_event.payload)
    assert payload.policy_decision is not None
    assert payload.policy_decision.outcome == PolicyDecisionOutcome.ALLOW
    assert payload.tool_call.status.value == "succeeded"

    audit_events = [
        event for event in run_service.list_run_events(result.run_id) if event.event_type == RunEventType.AUDIT_RECORDED
    ]
    assert len(audit_events) == 1
    audit_payload = cast(AuditRecordedPayload, audit_events[0].payload)
    assert audit_payload.audit_record["event_kind"] == AuditEventKind.POLICY_EVALUATED
    assert audit_payload.audit_record["payload"] == {"test": True}


def test_worker_exposes_approval_required_path_through_bastion(tmp_path: Path) -> None:
    run_service = _MemoryRunService()
    helpdesk_service = HelpdeskService.seeded("seed-phase3-demo")
    bastion_gateway = _ApprovalBastionGateway()
    model_gateway = ModelGateway(
        FakeModelProvider(
            scripted_responses=(
                ModelResponse(
                    tool_request=ToolRequest(
                        request_id="toolreq-ticket-001",
                        tool_name="helpdesk_ticket",
                        arguments={"action": "add_note", "ticket_id": "ticket_mfa_reenrollment_device_loss", "author": "agent.phase5", "note_body": "Need approval.", "note_kind": "internal"},
                    ),
                    metadata={"summary": "Attempt an approval-gated mutation"},
                ),
            )
        )
    )

    result = execute_seeded_agent_run(
        cast(Any, run_service),
        spec=SeededAgentRunSpec(run_id="bastion-approval-001"),
        agent_config=_single_tool_agent_config("helpdesk_ticket"),
        model_gateway=model_gateway,
        bastion_gateway=bastion_gateway,
        helpdesk_service=helpdesk_service,
        browser_runner=_FakeBrowserRunner(),
        artifact_storage_dir=str(tmp_path / "artifacts"),
    )

    assert len(bastion_gateway.requests) == 1
    assert result.final_status == RunStatus.WAITING_APPROVAL
    tool_event = next(
        event
        for event in run_service.list_run_events(result.run_id)
        if event.event_type.value == "tool_call.recorded"
    )
    payload = cast(ToolCallRecordedPayload, tool_event.payload)
    assert payload.policy_decision is not None
    assert payload.policy_decision.outcome == PolicyDecisionOutcome.REQUIRE_APPROVAL
    assert payload.tool_call.status.value == "blocked"

    approval_event = next(
        event
        for event in run_service.list_run_events(result.run_id)
        if event.event_type == RunEventType.APPROVAL_REQUESTED
    )
    approval_payload = cast(ApprovalRequestedPayload, approval_event.payload)
    assert approval_payload.approval_request["approval_request_id"] == "approval-toolreq-ticket-001"

    waiting_event = next(
        event
        for event in run_service.list_run_events(result.run_id)
        if event.event_type == RunEventType.RUN_WAITING_APPROVAL
    )
    waiting_payload = cast(RunWaitingApprovalPayload, waiting_event.payload)
    assert waiting_payload.approval_request_id == "approval-toolreq-ticket-001"


def test_worker_persists_bastion_audit_records_for_approval_gated_requests(tmp_path: Path) -> None:
    run_service = _MemoryRunService()
    helpdesk_service = HelpdeskService.seeded("seed-phase3-demo")
    requested_at = datetime(2026, 3, 16, 12, 0)

    class _ApprovalAuditBastionGateway(_ApprovalBastionGateway):
        def handle_tool_request(
            self,
            request: BastionToolRequest,
            *,
            executor=None,
        ) -> BastionToolResponse:
            response = super().handle_tool_request(request, executor=executor)
            return response.model_copy(
                update={
                    "audit_records": (
                        AuditRecordEnvelope(
                            audit_id=f"audit-policy-{request.request_id}",
                            run_id=request.run_id,
                            step_id=request.step_id,
                            request_id=request.request_id,
                            actor_type=ActorType.BASTION,
                            event_kind=AuditEventKind.POLICY_EVALUATED,
                            occurred_at=cast(datetime, request.requested_at),
                            payload={"decision": "require_approval"},
                        ),
                        AuditRecordEnvelope(
                            audit_id=f"audit-approval-{request.request_id}",
                            run_id=request.run_id,
                            step_id=request.step_id,
                            request_id=request.request_id,
                            actor_type=ActorType.BASTION,
                            event_kind=AuditEventKind.APPROVAL_REQUESTED,
                            occurred_at=cast(datetime, request.requested_at),
                            payload={"approvalRequestId": f"approval-{request.request_id}"},
                        ),
                    )
                }
            )

    bastion_gateway = _ApprovalAuditBastionGateway()
    model_gateway = ModelGateway(
        FakeModelProvider(
            scripted_responses=(
                ModelResponse(
                    tool_request=ToolRequest(
                        request_id="toolreq-ticket-002",
                        tool_name="helpdesk_ticket",
                        arguments={
                            "action": "add_note",
                            "ticket_id": "ticket_mfa_reenrollment_device_loss",
                            "author": "agent.phase5",
                            "note_body": "Need approval.",
                            "note_kind": "internal",
                        },
                        requested_at=requested_at,
                    ),
                    metadata={"summary": "Attempt an approval-gated mutation"},
                ),
            )
        )
    )

    result = execute_seeded_agent_run(
        cast(Any, run_service),
        spec=SeededAgentRunSpec(run_id="bastion-approval-audit-001"),
        agent_config=_single_tool_agent_config("helpdesk_ticket"),
        model_gateway=model_gateway,
        bastion_gateway=bastion_gateway,
        helpdesk_service=helpdesk_service,
        browser_runner=_FakeBrowserRunner(),
        artifact_storage_dir=str(tmp_path / "artifacts"),
    )

    assert result.final_status == RunStatus.WAITING_APPROVAL
    audit_events = [
        event for event in run_service.list_run_events(result.run_id) if event.event_type == RunEventType.AUDIT_RECORDED
    ]
    assert [cast(AuditRecordedPayload, event.payload).audit_record["event_kind"] for event in audit_events] == [
        AuditEventKind.POLICY_EVALUATED,
        AuditEventKind.APPROVAL_REQUESTED,
    ]


def test_worker_interrupts_active_run_after_stop_requested(tmp_path: Path) -> None:
    run_service = _MemoryRunService()
    helpdesk_service = HelpdeskService.seeded("seed-phase3-demo")

    class _StopRequestingBastionGateway(_RecordingBastionGateway):
        def __init__(self) -> None:
            super().__init__()
            self.stop_requested = False

        def handle_tool_request(
            self,
            request: BastionToolRequest,
            *,
            executor=None,
        ) -> BastionToolResponse:
            response = super().handle_tool_request(request, executor=executor)
            if not self.stop_requested:
                requested_at = cast(datetime, request.requested_at)
                run_service.append_run_event(
                    RunEvent(
                        event_id=f"{request.run_id}-event-stop-requested-stop_001",
                        run_id=request.run_id,
                        sequence=run_service.next_event_sequence(request.run_id),
                        occurred_at=requested_at,
                        source=RunEventSource.OPERATOR,
                        actor_type=ActorType.OPERATOR,
                        correlation_id="stop_001",
                        event_type=RunEventType.RUN_STOP_REQUESTED,
                        payload=RunStopRequestedPayload(
                            event_type=RunEventType.RUN_STOP_REQUESTED,
                            run_id=request.run_id,
                            stop_request_id="stop_001",
                            operator_id="operator_123",
                            requested_at=requested_at,
                            reason="Interrupt the run after the first safe boundary.",
                        ),
                    )
                )
                run_service.append_run_event(
                    RunEvent(
                        event_id=f"{request.run_id}-event-audit-stop-requested-stop_001",
                        run_id=request.run_id,
                        sequence=run_service.next_event_sequence(request.run_id),
                        occurred_at=requested_at,
                        source=RunEventSource.OPERATOR,
                        actor_type=ActorType.OPERATOR,
                        correlation_id="stop_001",
                        event_type=RunEventType.AUDIT_RECORDED,
                        payload=AuditRecordedPayload(
                            event_type=RunEventType.AUDIT_RECORDED,
                            run_id=request.run_id,
                            audit_record=AuditRecordEnvelope(
                                audit_id="audit-stop-requested-stop_001",
                                run_id=request.run_id,
                                actor_type=ActorType.OPERATOR,
                                event_kind=AuditEventKind.KILL_SWITCH_TRIGGERED,
                                occurred_at=requested_at,
                                payload={
                                    "phase": "requested",
                                    "stopRequestId": "stop_001",
                                    "operatorId": "operator_123",
                                },
                            ).model_dump(mode="json"),
                        ),
                    )
                )
                self.stop_requested = True
            return response

    bastion_gateway = _StopRequestingBastionGateway()
    model_gateway = ModelGateway(
        FakeModelProvider(
            scripted_responses=(
                ModelResponse(
                    tool_request=ToolRequest(
                        request_id="toolreq-doc-stop-001",
                        tool_name="document_lookup",
                        arguments={"action": "get_document", "slug": "mfa-device-loss-playbook"},
                    ),
                    metadata={"summary": "Read the MFA SOP"},
                ),
                ModelResponse(
                    final_output="This should never be reached.",
                    metadata={"summary": "Finish the run"},
                ),
            )
        )
    )

    result = execute_seeded_agent_run(
        cast(Any, run_service),
        spec=SeededAgentRunSpec(run_id="bastion-stop-001"),
        agent_config=_single_tool_agent_config("document_lookup"),
        model_gateway=model_gateway,
        bastion_gateway=bastion_gateway,
        helpdesk_service=helpdesk_service,
        browser_runner=_FakeBrowserRunner(),
        artifact_storage_dir=str(tmp_path / "artifacts"),
    )

    assert result.final_status == RunStatus.CANCELLED
    assert result.termination_reason.value == "cancelled"
    assert result.final_output is None

    completed_event = next(
        event
        for event in run_service.list_run_events(result.run_id)
        if event.event_type == RunEventType.RUN_COMPLETED
    )
    completed_payload = cast(RunCompletedPayload, completed_event.payload)
    assert completed_payload.final_status == RunStatus.CANCELLED
    assert completed_payload.grade_result is not None
    assert completed_payload.grade_result.details["interruptedByKillSwitch"] is True

    kill_switch_audits = [
        cast(AuditRecordedPayload, event.payload).audit_record
        for event in run_service.list_run_events(result.run_id)
        if event.event_type == RunEventType.AUDIT_RECORDED
        and cast(AuditRecordedPayload, event.payload).audit_record["event_kind"]
        == AuditEventKind.KILL_SWITCH_TRIGGERED
    ]
    assert [record["payload"]["phase"] for record in kill_switch_audits] == [
        "requested",
        "completed",
    ]


def test_seeded_multi_tool_run_routes_all_phase4_tools_through_bastion(tmp_path: Path) -> None:
    run_service = _MemoryRunService()
    helpdesk_service = HelpdeskService.seeded("seed-phase3-demo")
    bastion_gateway = _RecordingBastionGateway()
    model_gateway = ModelGateway(
        FakeModelProvider(
            scripted_responses=(
                ModelResponse(
                    tool_request=ToolRequest(
                        request_id="toolreq-doc-multi-001",
                        tool_name="document_lookup",
                        arguments={"action": "search_documents", "query": "mfa device loss"},
                    ),
                    metadata={"summary": "Review the MFA recovery SOP"},
                ),
                ModelResponse(
                    tool_request=ToolRequest(
                        request_id="toolreq-dir-multi-001",
                        tool_name="directory_lookup",
                        arguments={"action": "search_employees", "name": "Tessa"},
                    ),
                    metadata={"summary": "Find the affected employee record"},
                ),
                ModelResponse(
                    tool_request=ToolRequest(
                        request_id="toolreq-browser-multi-001",
                        tool_name="browser",
                        arguments={"action": "open", "target": "/internal/helpdesk"},
                    ),
                    metadata={"summary": "Open the seeded helpdesk surface"},
                ),
                ModelResponse(
                    tool_request=ToolRequest(
                        request_id="toolreq-ticket-multi-001",
                        tool_name="helpdesk_ticket",
                        arguments={
                            "action": "get_ticket",
                            "ticket_id": "ticket_mfa_reenrollment_device_loss",
                        },
                    ),
                    metadata={"summary": "Read the seeded ticket"},
                ),
                ModelResponse(
                    tool_request=ToolRequest(
                        request_id="toolreq-shot-multi-001",
                        tool_name="screenshot_capture",
                        arguments={"scope": "page", "label": "phase5-multi-tool"},
                    ),
                    metadata={"summary": "Capture screenshot evidence"},
                ),
                ModelResponse(
                    tool_request=ToolRequest(
                        request_id="toolreq-ticket-multi-002",
                        tool_name="helpdesk_ticket",
                        arguments={
                            "action": "add_note",
                            "ticket_id": "ticket_mfa_reenrollment_device_loss",
                            "author": "agent.phase5",
                            "note_body": "Access restored after re-enrollment and verification.",
                            "note_kind": "resolution",
                        },
                    ),
                    metadata={"summary": "Document restored access in the ticket"},
                ),
                ModelResponse(
                    tool_request=ToolRequest(
                        request_id="toolreq-ticket-multi-003",
                        tool_name="helpdesk_ticket",
                        arguments={
                            "action": "update_status",
                            "ticket_id": "ticket_mfa_reenrollment_device_loss",
                            "status": "resolved",
                        },
                    ),
                    metadata={"summary": "Resolve the ticket"},
                ),
                ModelResponse(
                    final_output="MFA re-enrollment is complete and the ticket is resolved.",
                    metadata={
                        "summary": "Finish the run after successful verification",
                        "completed_checks": (
                            "identity_proofing_confirmed",
                            "access_restored_verified",
                        ),
                    },
                ),
            )
        )
    )

    result = execute_seeded_agent_run(
        cast(Any, run_service),
        spec=SeededAgentRunSpec(run_id="bastion-multi-tool-001"),
        agent_config=AgentConfig(
            provider="fake",
            model_name="phase5-fake",
            deterministic=True,
            temperature=0.0,
            max_steps=8,
            retry_policy=RetryPolicy(max_attempts=1),
            allowed_tool_names=(
                "document_lookup",
                "directory_lookup",
                "browser",
                "helpdesk_ticket",
                "screenshot_capture",
            ),
        ),
        model_gateway=model_gateway,
        bastion_gateway=bastion_gateway,
        helpdesk_service=helpdesk_service,
        browser_runner=_FakeBrowserRunner(),
        artifact_storage_dir=str(tmp_path / "artifacts"),
    )

    assert result.final_status == RunStatus.SUCCEEDED
    assert [request.tool_request.tool_name for request in bastion_gateway.requests] == [
        "document_lookup",
        "directory_lookup",
        "browser",
        "helpdesk_ticket",
        "screenshot_capture",
        "helpdesk_ticket",
        "helpdesk_ticket",
    ]
    assert result.artifact_count >= 1

    artifact_events = [
        event
        for event in run_service.list_run_events(result.run_id)
        if event.event_type == RunEventType.ARTIFACT_ATTACHED
    ]
    assert len(artifact_events) == 1

    tool_events = [
        cast(ToolCallRecordedPayload, event.payload)
        for event in run_service.list_run_events(result.run_id)
        if event.event_type == RunEventType.TOOL_CALL_RECORDED
    ]
    assert {payload.tool_call.tool_name for payload in tool_events} == {
        "document_lookup",
        "directory_lookup",
        "browser",
        "helpdesk_ticket",
        "screenshot_capture",
    }
    assert all(
        payload.policy_decision is not None
        and payload.policy_decision.outcome == PolicyDecisionOutcome.ALLOW
        for payload in tool_events
    )
