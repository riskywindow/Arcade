from __future__ import annotations

from contextlib import suppress
import ast
from collections.abc import Generator
import uuid

import psycopg
import pytest
from psycopg.rows import dict_row

from atlas_core import (
    GradeResult,
    GradeOutcome,
    ArtifactAttachedPayload,
    DEFAULT_MIGRATIONS_DIR,
    RunRepository,
    RunService,
    RunStatus,
    TerminationReason,
    apply_migrations,
    discover_migrations,
)
from atlas_core.config import InfrastructureConfig, ServiceConfig
from atlas_worker.agent_execution import AgentExecutionResult
from atlas_worker.config import WorkerConfig
from atlas_worker.dummy_execution import (
    DummyRunSpec,
    execute_dummy_run,
    execute_dummy_run_from_config,
)
from atlas_worker.main import main
from model_gateway import AgentConfig


def _connect() -> psycopg.Connection[dict[str, object]] | None:
    dsn = InfrastructureConfig.from_env().postgres_dsn()
    try:
        return psycopg.connect(dsn, autocommit=True, row_factory=dict_row)
    except psycopg.OperationalError:
        return None


@pytest.fixture
def isolated_worker_service() -> Generator[tuple[RunService, str], None, None]:
    conn = _connect()
    if conn is None:
        pytest.skip("local Postgres is not available")

    schema_name = f"test_worker_dummy_{uuid.uuid4().hex[:8]}"
    conn.execute(f'create schema "{schema_name}"')
    conn.execute("select set_config('search_path', %s, false)", (schema_name,))
    apply_migrations(conn, discover_migrations(DEFAULT_MIGRATIONS_DIR))

    service = RunService(RunRepository(conn))
    try:
        yield service, schema_name
    finally:
        with suppress(psycopg.Error):
            conn.execute(f'drop schema if exists "{schema_name}" cascade')
        conn.close()


def test_execute_dummy_run_creates_deterministic_sequence(
    isolated_worker_service: tuple[RunService, str],
) -> None:
    service, _ = isolated_worker_service
    spec = DummyRunSpec(run_id="dummy-run-test-001")

    result = execute_dummy_run(service, spec)

    assert result.run_id == "dummy-run-test-001"
    assert result.final_status.value == "succeeded"
    assert result.event_count == 7
    assert result.artifact_count == 1

    run = service.get_run(spec.run_id)
    assert run.status.value == "succeeded"
    assert run.started_at == spec.base_time.replace(second=10)
    assert run.completed_at == spec.base_time.replace(second=30)
    events = service.list_run_events(spec.run_id)
    assert [event.event_type.value for event in events] == [
        "run.created",
        "run.ready",
        "run.started",
        "run.step.created",
        "tool_call.recorded",
        "artifact.attached",
        "run.completed",
    ]
    assert [event.sequence for event in events] == [0, 1, 2, 3, 4, 5, 6]
    attached_artifact_event = events[5]
    assert isinstance(attached_artifact_event.payload, ArtifactAttachedPayload)
    assert attached_artifact_event.payload.artifact.run_id == spec.run_id
    assert attached_artifact_event.payload.artifact.step_id == f"{spec.run_id}-step-001"


def test_execute_dummy_run_from_config_uses_worker_path(
    isolated_worker_service: tuple[RunService, str],
) -> None:
    _, schema_name = isolated_worker_service
    config = WorkerConfig(
        service=ServiceConfig(
            service_name="atlas-worker",
            environment="test",
            host="127.0.0.1",
            port=8100,
            log_level="INFO",
            reload=False,
        ),
        infrastructure=InfrastructureConfig.from_env(),
        agent=AgentConfig(provider="fake", model_name="phase4-fake"),
        artifact_storage_dir="/tmp/atlas-artifacts-tests",
    )
    result = execute_dummy_run_from_config(
        config,
        DummyRunSpec(run_id="dummy-run-test-002"),
        schema_name=schema_name,
    )

    assert result.run_id == "dummy-run-test-002"
    assert result.event_count == 7


def test_worker_main_dummy_run_command(
    isolated_worker_service: tuple[RunService, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, schema_name = isolated_worker_service
    monkeypatch.setattr(
        "sys.argv",
        [
            "atlas-worker",
            "dummy-run",
            "--run-id",
            "dummy-run-cli-001",
            "--schema-name",
            schema_name,
        ],
    )

    main()

    output = ast.literal_eval(capsys.readouterr().out.strip())
    assert output == {
        "run_id": "dummy-run-cli-001",
        "final_status": "succeeded",
        "event_count": 7,
        "artifact_count": 1,
    }


def test_worker_main_agent_demo_command(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _fake_execute_seeded_agent_run_from_config(*args, **kwargs) -> AgentExecutionResult:
        del args, kwargs
        return AgentExecutionResult(
            run_id="phase4-agent-demo-cli-001",
            scenario_id="mfa-reenrollment-device-loss",
            final_status=RunStatus.SUCCEEDED,
            termination_reason=TerminationReason.SUCCESS,
            grade_result=GradeResult(
                outcome=GradeOutcome.PASSED,
                score=1.0,
                summary="Seeded MFA scenario passed.",
            ),
            event_count=18,
            artifact_count=1,
            final_output="MFA re-enrollment is complete and the ticket is resolved.",
        )

    monkeypatch.setattr(
        "atlas_worker.main.execute_seeded_agent_run_from_config",
        _fake_execute_seeded_agent_run_from_config,
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "atlas-worker",
            "agent-demo",
            "--run-id",
            "phase4-agent-demo-cli-001",
            "--scenario-id",
            "mfa-reenrollment-device-loss",
            "--seed",
            "seed-phase3-demo",
        ],
    )

    main()

    output = ast.literal_eval(capsys.readouterr().out.strip())
    assert output == {
        "run_id": "phase4-agent-demo-cli-001",
        "scenario_id": "mfa-reenrollment-device-loss",
        "final_status": "succeeded",
        "termination_reason": "success",
        "event_count": 18,
        "artifact_count": 1,
        "browser_mode": "stub",
    }
