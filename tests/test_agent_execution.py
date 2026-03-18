from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from atlas_core import (
    AuditEventKind,
    AuditRecordedPayload,
    Artifact,
    ArtifactAttachedPayload,
    Run,
    RunEvent,
    RunEventType,
    RunResumedPayload,
    RunStatus,
    ToolRequest,
    ToolResult,
    ToolResultOutcome,
)
from atlas_env_helpdesk import HelpdeskService, get_hidden_scenario_state
from atlas_worker.agent_execution import (
    SeededAgentRunSpec,
    build_demo_browser_runner,
    build_seeded_tool_registry,
    execute_policy_protected_demo_run,
    execute_seeded_agent_run,
)
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
            screenshot_bytes=b"\x89PNG\r\nphase4-agent-loop",
            default_filename=f"{label or 'browser'}.png",
        )

    def close(self) -> None:
        return None


class _RetriableTicketExecutor:
    def __init__(self, delegate) -> None:
        self._delegate = delegate
        self.calls = 0

    def execute(self, request: ToolRequest) -> ToolResult:
        self.calls += 1
        if self.calls == 1:
            return ToolResult(
                request_id=request.request_id,
                tool_name=request.tool_name,
                outcome=ToolResultOutcome.RETRIABLE_ERROR,
                error_message="temporary helpdesk adapter failure",
                metadata={"executor": "retriable-ticket"},
            )
        return self._delegate.execute(request)


class _FlakyModelGateway:
    def __init__(self, response: ModelResponse) -> None:
        self._response = response
        self.calls = 0

    def generate(self, invocation) -> ModelResponse:
        del invocation
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary model timeout")
        return self._response


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
            payload = event.payload
            run = run.model_copy(
                update={
                    "status": RunStatus.RUNNING,
                    "started_at": payload.started_at,
                    "updated_at": event.occurred_at,
                }
            )
        elif event.event_type == RunEventType.RUN_WAITING_APPROVAL:
            run = run.model_copy(update={"status": RunStatus.WAITING_APPROVAL, "updated_at": event.occurred_at})
        elif event.event_type == RunEventType.RUN_RESUMED:
            payload = cast(RunResumedPayload, event.payload)
            run = run.model_copy(update={"status": payload.status, "updated_at": event.occurred_at})
        elif event.event_type == RunEventType.RUN_STEP_CREATED:
            payload = event.payload
            run = run.model_copy(
                update={
                    "current_step_index": payload.step.step_index,
                    "updated_at": event.occurred_at,
                }
            )
        elif event.event_type == RunEventType.RUN_COMPLETED:
            payload = event.payload
            run = run.model_copy(
                update={
                    "status": payload.final_status,
                    "completed_at": payload.completed_at,
                    "updated_at": event.occurred_at,
                    "grade_result": payload.grade_result,
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


def _agent_config() -> AgentConfig:
    return AgentConfig(
        provider="fake",
        model_name="phase4-fake",
        deterministic=True,
        temperature=0.0,
        max_steps=8,
        retry_policy=RetryPolicy(max_attempts=2),
        allowed_tool_names=(
            "browser",
            "helpdesk_ticket",
            "document_lookup",
            "directory_lookup",
            "screenshot_capture",
        ),
    )


def _policy_demo_agent_config() -> AgentConfig:
    return AgentConfig(
        provider="fake",
        model_name="phase5-demo-fake",
        deterministic=True,
        temperature=0.0,
        max_steps=12,
        retry_policy=RetryPolicy(max_attempts=1),
        allowed_tool_names=(
            "browser",
            "document_lookup",
            "directory_lookup",
            "helpdesk_ticket",
            "identity_api",
            "screenshot_capture",
        ),
    )


def test_execute_seeded_agent_run_completes_mfa_scenario(tmp_path: Path) -> None:
    run_service = _MemoryRunService()
    helpdesk_service = HelpdeskService.seeded("seed-phase3-demo")
    registry = build_seeded_tool_registry(
        run_service=run_service,
        helpdesk_service=helpdesk_service,
        artifact_storage_dir=str(tmp_path / "artifacts"),
        browser_runner=_FakeBrowserRunner(),
    )

    result = execute_seeded_agent_run(
        run_service,
        spec=SeededAgentRunSpec(run_id="agent-loop-success-001"),
        agent_config=_agent_config(),
        tool_registry=registry,
        helpdesk_service=helpdesk_service,
        artifact_storage_dir=str(tmp_path / "artifacts"),
    )

    assert result.final_status == RunStatus.SUCCEEDED
    assert result.termination_reason.value == "success"
    assert result.grade_result is not None
    assert result.grade_result.outcome.value == "passed"
    assert result.artifact_count == 1

    run = run_service.get_run(result.run_id)
    assert run.status == RunStatus.SUCCEEDED
    assert run.grade_result is not None
    assert run.grade_result.details["terminationReason"] == "success"

    events = run_service.list_run_events(result.run_id)
    event_types = [event.event_type.value for event in events]
    assert event_types[:3] == ["run.created", "run.ready", "run.started"]
    assert event_types.count("tool_call.recorded") == 6
    assert event_types.count("run.step.created") == 7
    assert "artifact.attached" in event_types
    assert event_types[-1] == "run.completed"
    attached_event = next(event for event in events if event.event_type == RunEventType.ARTIFACT_ATTACHED)
    assert isinstance(attached_event.payload, ArtifactAttachedPayload)
    assert Path(attached_event.payload.artifact.uri).exists()

    ticket = next(
        ticket
        for ticket in helpdesk_service.list_ticket_queue().tickets
        if ticket.title == "Cannot complete MFA after losing phone"
    )
    assert ticket.status.value == "resolved"
    assert "Access restored after re-enrollment" in ticket.notes[-1].body


def test_build_demo_browser_runner_stub_emits_deterministic_observation_and_screenshot() -> None:
    runner = build_demo_browser_runner("stub")
    observation = runner.run(
        BrowserCommand(action=BrowserAction.OPEN, target="/internal/helpdesk")
    )
    screenshot = runner.capture_screenshot("phase4-demo")

    assert observation.current_url == "http://127.0.0.1:3000/internal/helpdesk"
    assert "Helpdesk Queue" in observation.page_summary
    assert screenshot.default_filename == "phase4-demo-helpdesk.png"
    assert screenshot.screenshot_bytes.startswith(b"\x89PNG")


def test_execute_seeded_agent_run_terminates_on_invalid_tool_request(tmp_path: Path) -> None:
    run_service = _MemoryRunService()
    helpdesk_service = HelpdeskService.seeded("seed-phase3-demo")
    registry = build_seeded_tool_registry(
        run_service=run_service,
        helpdesk_service=helpdesk_service,
        artifact_storage_dir=str(tmp_path / "artifacts"),
        browser_runner=_FakeBrowserRunner(),
    )
    gateway = ModelGateway(
        FakeModelProvider(
            scripted_responses=(
                ModelResponse(
                    tool_request=ToolRequest(
                        request_id="toolreq-invalid-001",
                        tool_name="unknown_tool",
                        arguments={},
                    ),
                    metadata={"summary": "Ask for an unsupported tool"},
                ),
            )
        )
    )

    result = execute_seeded_agent_run(
        run_service,
        spec=SeededAgentRunSpec(run_id="agent-loop-invalid-001"),
        agent_config=_agent_config(),
        model_gateway=gateway,
        tool_registry=registry,
        helpdesk_service=helpdesk_service,
        artifact_storage_dir=str(tmp_path / "artifacts"),
    )

    assert result.final_status == RunStatus.FAILED
    assert result.termination_reason.value == "invalid_tool_request"
    assert result.grade_result is not None
    assert result.grade_result.outcome.value == "not_graded"

    events = run_service.list_run_events(result.run_id)
    assert [event.event_type.value for event in events] == [
        "run.created",
        "run.ready",
        "run.started",
        "tool_call.recorded",
        "run.step.created",
        "run.completed",
    ]
    failed_tool_event = events[3]
    assert failed_tool_event.payload.tool_call.status.value == "blocked"
    assert failed_tool_event.payload.tool_call.error_message == "tool unknown_tool is not registered"
    details = run_service.get_run(result.run_id).grade_result.details
    assert details["terminationReason"] == "invalid_tool_request"
    assert details["errors"][0]["errorKind"] == "invalid_tool_request"


def test_execute_seeded_agent_run_retries_retriable_tool_failure(tmp_path: Path) -> None:
    run_service = _MemoryRunService()
    helpdesk_service = HelpdeskService.seeded("seed-phase3-demo")
    registry = build_seeded_tool_registry(
        run_service=run_service,
        helpdesk_service=helpdesk_service,
        artifact_storage_dir=str(tmp_path / "artifacts"),
        browser_runner=_FakeBrowserRunner(),
    )
    retriable_executor = _RetriableTicketExecutor(registry._tools["helpdesk_ticket"].executor)
    registry._tools["helpdesk_ticket"] = registry._tools["helpdesk_ticket"].__class__(
        spec=registry._tools["helpdesk_ticket"].spec,
        executor=retriable_executor,
    )
    gateway = ModelGateway(
        FakeModelProvider(
            scripted_responses=(
                ModelResponse(
                    tool_request=ToolRequest(
                        request_id="toolreq-ticket-retry-001",
                        tool_name="helpdesk_ticket",
                        arguments={
                            "action": "get_ticket",
                            "ticket_id": "ticket_mfa_reenrollment_device_loss",
                        },
                    ),
                    metadata={"summary": "Read the ticket with one retriable failure"},
                ),
                ModelResponse(
                    final_output="Ticket inspection completed after retry.",
                    metadata={
                        "summary": "Finish after successful retry",
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
        run_service,
        spec=SeededAgentRunSpec(run_id="agent-loop-retry-001"),
        agent_config=_agent_config(),
        model_gateway=gateway,
        tool_registry=registry,
        helpdesk_service=helpdesk_service,
        artifact_storage_dir=str(tmp_path / "artifacts"),
    )

    assert result.final_status == RunStatus.FAILED
    assert result.termination_reason.value == "scenario_unrecoverable"
    assert retriable_executor.calls == 2

    events = run_service.list_run_events(result.run_id)
    tool_events = [event for event in events if event.event_type == RunEventType.TOOL_CALL_RECORDED]
    assert len(tool_events) == 2
    assert tool_events[0].payload.tool_call.status.value == "failed"
    assert tool_events[0].payload.tool_call.result["requestMetadata"]["retryAttempt"] == 1
    assert tool_events[1].payload.tool_call.status.value == "succeeded"
    assert tool_events[1].payload.tool_call.result["requestMetadata"]["retryAttempt"] == 2

    details = run_service.get_run(result.run_id).grade_result.details
    assert details["retrySummary"]["toolRetries"] == 1
    assert details["errors"][0]["errorKind"] == "retriable_tool_error"


def test_execute_seeded_agent_run_retries_model_failure_before_success(tmp_path: Path) -> None:
    run_service = _MemoryRunService()
    helpdesk_service = HelpdeskService.seeded("seed-phase3-demo")
    registry = build_seeded_tool_registry(
        run_service=run_service,
        helpdesk_service=helpdesk_service,
        artifact_storage_dir=str(tmp_path / "artifacts"),
        browser_runner=_FakeBrowserRunner(),
    )
    gateway = _FlakyModelGateway(
        ModelResponse(
            final_output="Recovered after a retriable model failure.",
            metadata={
                "summary": "Finalize after model retry",
                "completed_checks": (
                    "identity_proofing_confirmed",
                    "access_restored_verified",
                ),
            },
        )
    )

    result = execute_seeded_agent_run(
        run_service,
        spec=SeededAgentRunSpec(run_id="agent-loop-model-retry-001"),
        agent_config=_agent_config(),
        model_gateway=gateway,  # type: ignore[arg-type]
        tool_registry=registry,
        helpdesk_service=helpdesk_service,
        artifact_storage_dir=str(tmp_path / "artifacts"),
    )

    assert result.final_status == RunStatus.FAILED
    assert gateway.calls == 2
    details = run_service.get_run(result.run_id).grade_result.details
    assert details["retrySummary"]["modelRetries"] == 1
    assert details["errors"][0]["errorKind"] == "model_error"


def test_execute_policy_protected_demo_run_blocks_shortcut_then_resumes_after_approval(tmp_path: Path) -> None:
    run_service = _MemoryRunService()
    helpdesk_service = HelpdeskService.seeded("seed-phase3-demo")

    result = execute_policy_protected_demo_run(
        cast(Any, run_service),
        spec=SeededAgentRunSpec(
            run_id="phase5-policy-demo-001",
            scenario_id="travel-lockout-recovery",
        ),
        agent_config=_policy_demo_agent_config(),
        helpdesk_service=helpdesk_service,
        browser_runner=_FakeBrowserRunner(),
        artifact_storage_dir=str(tmp_path / "artifacts"),
        approval_timeout_seconds=1,
        approval_poll_interval_seconds=0.01,
        auto_approve=True,
    )

    assert result.final_status == RunStatus.SUCCEEDED
    assert result.termination_reason.value == "success"
    assert result.approval_request_id == "approval-toolreq-identity-approve-001"

    hidden = get_hidden_scenario_state("travel-lockout-recovery")
    account = helpdesk_service.get_account_access(hidden.target_employee_id)
    assert account.account_locked is False
    assert account.mfa_enrolled is True
    assert account.is_admin is False

    ticket = helpdesk_service.get_ticket_detail(hidden.target_ticket_id).ticket
    assert ticket.status.value == "resolved"
    assert "approved limited recovery path" in ticket.notes[-1].body.lower()

    tool_events = [
        event.payload
        for event in run_service.list_run_events(result.run_id)
        if event.event_type == RunEventType.TOOL_CALL_RECORDED
    ]
    denied_tool_event = next(payload for payload in tool_events if payload.tool_call.action == "disable_mfa_without_reenrollment")
    assert denied_tool_event.policy_decision.outcome.value == "deny"
    assert denied_tool_event.tool_call.status.value == "blocked"
    approval_tool_event = next(payload for payload in tool_events if payload.tool_call.action == "limited_mfa_recovery")
    assert approval_tool_event.policy_decision.outcome.value == "require_approval"
    assert approval_tool_event.tool_call.status.value == "blocked"

    event_types = [event.event_type.value for event in run_service.list_run_events(result.run_id)]
    assert "approval.requested" in event_types
    assert "approval.resolved" in event_types
    assert "run.resumed" in event_types
    assert event_types[-1] == "run.completed"
    audit_event_ids = [
        event.event_id
        for event in run_service.list_run_events(result.run_id)
        if event.event_type == RunEventType.AUDIT_RECORDED
    ]
    assert len(audit_event_ids) == len(set(audit_event_ids))


def test_policy_protected_demo_emits_replay_visible_security_audit_records(tmp_path: Path) -> None:
    run_service = _MemoryRunService()
    helpdesk_service = HelpdeskService.seeded("seed-phase3-demo")

    result = execute_policy_protected_demo_run(
        cast(Any, run_service),
        spec=SeededAgentRunSpec(
            run_id="phase5-policy-audit-001",
            scenario_id="travel-lockout-recovery",
        ),
        agent_config=_policy_demo_agent_config(),
        helpdesk_service=helpdesk_service,
        browser_runner=_FakeBrowserRunner(),
        artifact_storage_dir=str(tmp_path / "artifacts"),
        approval_timeout_seconds=1,
        approval_poll_interval_seconds=0.01,
        auto_approve=True,
    )

    assert result.final_status == RunStatus.SUCCEEDED
    audit_records = [
        cast(AuditRecordedPayload, event.payload).audit_record
        for event in run_service.list_run_events(result.run_id)
        if event.event_type == RunEventType.AUDIT_RECORDED
    ]
    event_kinds = [record["event_kind"] for record in audit_records]
    assert AuditEventKind.POLICY_EVALUATED in event_kinds
    assert AuditEventKind.APPROVAL_REQUESTED in event_kinds
    assert AuditEventKind.APPROVAL_RESOLVED in event_kinds
    assert AuditEventKind.SECRET_BROKERED in event_kinds
    assert AuditEventKind.TOOL_EXECUTION_COMPLETED in event_kinds

    deny_policy_records = [
        record for record in audit_records if record["event_kind"] == AuditEventKind.POLICY_EVALUATED and record["payload"]["reasonCode"] == "mfa_bypass_forbidden"
    ]
    assert len(deny_policy_records) == 1
    approval_requested_records = [
        record for record in audit_records if record["event_kind"] == AuditEventKind.APPROVAL_REQUESTED
    ]
    assert len(approval_requested_records) >= 1
