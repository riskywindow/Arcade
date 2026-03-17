from __future__ import annotations

from datetime import UTC, datetime

from atlas_core import (
    ActorType,
    BastionToolRequest,
    EnvironmentRef,
    PolicyCategory,
    PolicyDecisionOutcome,
    SandboxExecutionRequest,
    SandboxExecutionResult,
    SandboxMode,
    ScenarioRef,
    TaskRef,
    ToolRequest,
)
from atlas_worker import IsolatedCommandToolExecutor, isolated_command_tool_spec
from bastion_gateway import BastionGatewayService, StaticPolicyEvaluator
from bastion_gateway.sandbox import DockerSandboxRunner


class _FakeSandboxRunner:
    def __init__(self) -> None:
        self.requests: list[SandboxExecutionRequest] = []

    def run(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        self.requests.append(request)
        return SandboxExecutionResult(
            mode=SandboxMode.DOCKER,
            command=request.command,
            image=request.image,
            exit_code=0,
            stdout="Python 3.12.0\n",
            stderr="",
        )


def _tool_request() -> BastionToolRequest:
    return BastionToolRequest(
        request_id="toolreq_sandbox_001",
        run_id="run_sandbox_001",
        step_id="run_sandbox_001-step-001",
        turn_id="run_sandbox_001-turn-001",
        agent_id="agent_phase5",
        environment=EnvironmentRef(
            environment_id="env_helpdesk",
            environment_name="Northstar Helpdesk",
            environment_version="v1",
        ),
        scenario=ScenarioRef(
            scenario_id="travel-lockout",
            environment_id="env_helpdesk",
            scenario_name="Travel Lockout",
            scenario_seed="seed-123",
        ),
        task=TaskRef(
            task_id="task_123",
            scenario_id="travel-lockout",
            task_kind="access_restoration",
            task_title="Restore employee access after travel lockout",
        ),
        tool_request=ToolRequest(
            request_id="toolreq_sandbox_001",
            tool_name="isolated_command",
            arguments={"action": "python_version"},
            requested_at=datetime(2026, 3, 17, 12, 0, tzinfo=UTC),
        ),
        tool_spec=isolated_command_tool_spec(),
        requested_at=datetime(2026, 3, 17, 12, 0, tzinfo=UTC),
        metadata={"requesterRole": "helpdesk_agent"},
    )


def test_docker_sandbox_runner_builds_restricted_command() -> None:
    runner = DockerSandboxRunner()

    command = runner._docker_command(  # type: ignore[attr-defined]
        SandboxExecutionRequest(
            command=("python3", "--version"),
            image="atlas-bastion/sandbox-tools:local",
        )
    )

    assert command[:3] == ["docker", "run", "--rm"]
    assert "--network" in command
    assert "none" in command
    assert "--read-only" in command
    assert "atlas-bastion/sandbox-tools:local" in command


def test_bastion_gateway_executes_isolated_command_through_docker_runner() -> None:
    fake_runner = _FakeSandboxRunner()
    gateway = BastionGatewayService(
        policy_evaluator=StaticPolicyEvaluator(
            outcome=PolicyDecisionOutcome.ALLOW,
            category=PolicyCategory.SAFE_READ,
            rationale="sandbox_command_allowed",
        ),
        sandbox_runner=fake_runner,
    )

    response = gateway.handle_tool_request(
        _tool_request(),
        executor=IsolatedCommandToolExecutor(),
    )

    assert response.tool_result is not None
    assert response.tool_result.outcome.value == "success"
    assert response.tool_result.result == {
        "stdout": "Python 3.12.0",
        "action": "python_version",
    }
    assert fake_runner.requests[0].command == ("python3", "--version")
    execution_record = next(
        record for record in response.audit_records if record.event_kind == "tool_execution_completed"
    )
    assert execution_record.payload["sandboxed"] is True
    assert execution_record.actor_type == ActorType.BASTION


def test_isolated_command_executor_rejects_direct_non_sandboxed_execution() -> None:
    executor = IsolatedCommandToolExecutor()
    result = executor.execute(
        ToolRequest(
            request_id="toolreq_direct_001",
            tool_name="isolated_command",
            arguments={"action": "python_version"},
        )
    )

    assert result.outcome.value == "fatal_error"
    assert result.metadata["sandboxRequired"] is True
