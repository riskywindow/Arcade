from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from atlas_core import AgentTurn, EnvironmentRef, ExecutionContext, ScenarioRef, TaskRef, ToolRequest
from atlas_env_helpdesk import HelpdeskService
from atlas_worker.agent_execution import (
    SeededAgentRunSpec,
    _model_tool_definitions,
    build_seeded_execution_context,
    build_seeded_tool_registry,
)
from model_gateway import (
    AgentConfig,
    FakeModelProvider,
    ModelGateway,
    ModelInvocation,
    ModelResponse,
    ModelToolDefinition,
    RetryPolicy,
)


def _context() -> ExecutionContext:
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
        allowed_tool_names=("browser", "document_lookup", "helpdesk_ticket"),
    )


def _agent_config() -> AgentConfig:
    return AgentConfig(
        provider="fake",
        model_name="phase4-fake",
        temperature=0.0,
        deterministic=True,
        max_steps=6,
        retry_policy=RetryPolicy(max_attempts=2),
        allowed_tool_names=("browser", "document_lookup", "helpdesk_ticket"),
    )


def test_agent_config_rejects_nonzero_temperature_when_deterministic() -> None:
    with pytest.raises(ValidationError):
        AgentConfig(
            provider="fake",
            model_name="phase4-fake",
            temperature=0.3,
            deterministic=True,
        )


def test_model_response_requires_exactly_one_decision_path() -> None:
    with pytest.raises(ValidationError):
        ModelResponse()

    with pytest.raises(ValidationError):
        ModelResponse(
            tool_request=ToolRequest(
                request_id="toolreq_001",
                tool_name="document_lookup",
                arguments={"query": "mfa"},
            ),
            final_output="done",
        )


def test_fake_model_provider_replays_scripted_responses_and_holds_last_response() -> None:
    provider = FakeModelProvider(
        scripted_responses=(
            ModelResponse(
                tool_request=ToolRequest(
                    request_id="toolreq_001",
                    tool_name="document_lookup",
                    arguments={"query": "mfa device loss"},
                )
            ),
            ModelResponse(final_output="Resolved the task."),
        )
    )
    gateway = ModelGateway(provider)
    invocation = ModelInvocation(
        context=_context(),
        agent_config=_agent_config(),
        available_tools=(
            ModelToolDefinition(
                name="document_lookup",
                description="Search the internal SOP wiki.",
            ),
        ),
        turn_history=(
            AgentTurn(
                turn_id="turn_001",
                run_id="run_phase4_001",
                turn_index=1,
                summary="Search the wiki.",
                tool_request=ToolRequest(
                    request_id="toolreq_000",
                    tool_name="document_lookup",
                    arguments={"query": "mfa"},
                ),
            ),
        ),
    )

    first = gateway.generate(invocation)
    second = gateway.generate(invocation)
    third = gateway.generate(invocation)

    assert first.tool_request is not None
    assert second.final_output == "Resolved the task."
    assert third.final_output == "Resolved the task."


def test_fake_model_provider_requires_at_least_one_scripted_response() -> None:
    with pytest.raises(ValueError):
        FakeModelProvider(scripted_responses=())


def test_seeded_model_context_and_tool_definitions_do_not_expose_brokered_secret_values(tmp_path: Path) -> None:
    class _RunServiceStub:
        def attach_artifact(self, *, run_id, artifact, step_id=None):
            del run_id, step_id
            return artifact

        def append_run_event(self, event):
            return event

        def next_event_sequence(self, run_id):
            del run_id
            return 0

    registry = build_seeded_tool_registry(
        run_service=cast(Any, _RunServiceStub()),
        helpdesk_service=HelpdeskService.seeded("seed-phase3-demo"),
        artifact_storage_dir=str(tmp_path / "artifacts"),
    )
    context = build_seeded_execution_context(
        SeededAgentRunSpec(run_id="secret-context-001"),
        agent_config=_agent_config(),
        tool_registry=registry,
    )
    tool_definitions = _model_tool_definitions(registry)

    secret_value = "atlas-local-helpdesk-mutation-token"
    assert secret_value not in context.model_dump_json()
    assert all(secret_value not in definition.model_dump_json() for definition in tool_definitions)
