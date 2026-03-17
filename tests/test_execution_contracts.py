from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from atlas_core import (
    AgentRunner,
    AgentTurn,
    EnvironmentRef,
    ExecutionContext,
    RunExecutionSummary,
    RunStatus,
    ScenarioRef,
    TaskRef,
    TerminationReason,
    ToolRequest,
    ToolResult,
    ToolResultOutcome,
)


def _timestamp() -> datetime:
    return datetime(2026, 3, 16, 12, 0, tzinfo=UTC)


def _execution_context() -> ExecutionContext:
    return ExecutionContext(
        run_id="run_phase4_001",
        agent_id="agent_phase4",
        environment=EnvironmentRef(
            environment_id="env_helpdesk",
            environment_name="Northstar Helpdesk",
            environment_version="v1",
        ),
        scenario=ScenarioRef(
            scenario_id="mfa-reenrollment-device-loss",
            environment_id="env_helpdesk",
            scenario_name="MFA Re-Enrollment After Device Loss",
            scenario_seed="seed-mfa-reenrollment-device-loss",
        ),
        task=TaskRef(
            task_id="task_mfa_reenrollment_device_loss",
            scenario_id="mfa-reenrollment-device-loss",
            task_kind="access_restoration",
            task_title="Restore access after device loss",
        ),
        task_brief="Employee lost a phone and cannot complete MFA.",
        success_condition="Restore access through the approved MFA recovery path.",
        allowed_tool_names=("browser", "helpdesk_ticket", "document_lookup"),
        max_turns=6,
        metadata={"seed": "seed-phase4-demo"},
    )


def test_execution_context_round_trips_through_json() -> None:
    context = _execution_context()

    payload = context.model_dump_json()

    assert ExecutionContext.model_validate_json(payload) == context


def test_agent_turn_supports_tool_request_path() -> None:
    turn = AgentTurn(
        turn_id="turn_001",
        run_id="run_phase4_001",
        turn_index=1,
        summary="Look up the MFA recovery SOP before changing account state.",
        started_at=_timestamp(),
        completed_at=_timestamp(),
        tool_request=ToolRequest(
            request_id="toolreq_001",
            tool_name="document_lookup",
            arguments={"query": "mfa device loss"},
            requested_at=_timestamp(),
        ),
        tool_result=ToolResult(
            request_id="toolreq_001",
            tool_name="document_lookup",
            outcome=ToolResultOutcome.SUCCESS,
            result={"matchedSlug": "mfa-device-loss-playbook"},
        ),
    )

    assert turn.tool_request is not None
    assert turn.final_output is None


def test_agent_turn_supports_final_output_path() -> None:
    turn = AgentTurn(
        turn_id="turn_002",
        run_id="run_phase4_001",
        turn_index=2,
        summary="The task is complete after access is restored and the ticket is resolved.",
        final_output="Resolved the MFA recovery ticket after restoring the account.",
    )

    assert turn.final_output is not None
    assert turn.tool_request is None


def test_agent_turn_rejects_missing_or_duplicated_action_shape() -> None:
    with pytest.raises(ValidationError):
        AgentTurn(
            turn_id="turn_bad_001",
            run_id="run_phase4_001",
            turn_index=1,
            summary="Invalid turn without tool request or final output.",
        )

    with pytest.raises(ValidationError):
        AgentTurn(
            turn_id="turn_bad_002",
            run_id="run_phase4_001",
            turn_index=1,
            summary="Invalid turn with both tool request and final output.",
            tool_request=ToolRequest(
                request_id="toolreq_bad",
                tool_name="helpdesk_ticket",
                arguments={"ticketId": "ticket_123"},
            ),
            final_output="done",
        )


def test_tool_result_requires_error_message_for_non_success_outcomes() -> None:
    with pytest.raises(ValidationError):
        ToolResult(
            request_id="toolreq_002",
            tool_name="browser",
            outcome=ToolResultOutcome.RETRIABLE_ERROR,
        )

    with pytest.raises(ValidationError):
        ToolResult(
            request_id="toolreq_003",
            tool_name="browser",
            outcome=ToolResultOutcome.SUCCESS,
            error_message="should not be present",
        )


def test_run_execution_summary_is_serializable() -> None:
    summary = RunExecutionSummary(
        run_id="run_phase4_001",
        agent_id="agent_phase4",
        final_run_status=RunStatus.SUCCEEDED,
        termination_reason=TerminationReason.SUCCESS,
        turns_executed=4,
        steps_recorded=4,
        tool_calls_recorded=3,
        artifact_ids=("artifact_screenshot_001",),
        final_output="Access restored and the ticket is resolved.",
    )

    assert RunExecutionSummary.model_validate_json(summary.model_dump_json()) == summary


def test_agent_runner_protocol_is_runtime_checkable() -> None:
    class DummyRunner:
        def run(self, context: ExecutionContext) -> RunExecutionSummary:
            return RunExecutionSummary(
                run_id=context.run_id,
                agent_id=context.agent_id,
                final_run_status=RunStatus.SUCCEEDED,
                termination_reason=TerminationReason.SUCCESS,
                turns_executed=1,
                steps_recorded=1,
                tool_calls_recorded=0,
                final_output="done",
            )

    runner = DummyRunner()

    assert isinstance(runner, AgentRunner)
    assert runner.run(_execution_context()).termination_reason == TerminationReason.SUCCESS


def test_shared_types_export_phase_four_execution_contracts() -> None:
    source = Path("packages/shared-types/src/index.ts").read_text(encoding="utf-8")

    required_exports = (
        "export type ToolResultOutcome",
        "export type TerminationReason",
        "export type ToolRequest",
        "export type ToolResult",
        "export type AgentTurn",
        "export type ExecutionContext",
        "export type RunExecutionSummary",
    )

    for export_name in required_exports:
        assert export_name in source


def test_shared_types_export_phase_six_score_contracts() -> None:
    source = Path("packages/shared-types/src/index.ts").read_text(encoding="utf-8")

    required_exports = (
        "export type RunScorePolicyCounts",
        "export type RunScoreApprovalCounts",
        "export type RunScoreGraderSummary",
        "export type RunScoreSummary",
    )

    for export_name in required_exports:
        assert export_name in source


def test_shared_types_export_phase_six_benchmark_contracts() -> None:
    source = Path("packages/shared-types/src/index.ts").read_text(encoding="utf-8")

    required_exports = (
        "export type BenchmarkCatalogEntry",
        "export type BenchmarkCatalog",
        "export type BenchmarkRunItemResult",
        "export type BenchmarkRunAggregate",
        "export type BenchmarkRunResult",
    )

    for export_name in required_exports:
        assert export_name in source
