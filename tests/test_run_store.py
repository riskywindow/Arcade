from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime
import uuid
from collections.abc import Generator
from typing import Any, cast

import psycopg
import pytest

from atlas_core import (
    ActorType,
    Artifact,
    ArtifactAlreadyExistsError,
    ArtifactKind,
    DEFAULT_MIGRATIONS_DIR,
    EnvironmentRef,
    EventSequenceConflictError,
    GradeOutcome,
    GradeResult,
    InvalidRunEventTransitionError,
    InvalidRunFinalizationError,
    Run,
    RunAlreadyExistsError,
    RunCompletedPayload,
    RunCreatedPayload,
    RunEvent,
    RunEventSource,
    RunEventType,
    RunFinalization,
    RunNotFoundError,
    RunReadyPayload,
    RunRepository,
    RunService,
    RunStartedPayload,
    RunStatus,
    ScenarioRef,
    TaskRef,
    ToolCall,
    ToolCallRecordedPayload,
    ToolCallStatus,
    apply_migrations,
    discover_migrations,
    open_run_store_connection,
)
from atlas_core.config import InfrastructureConfig


def _timestamp() -> datetime:
    return datetime(2026, 3, 15, 12, 0, tzinfo=UTC)


def _run(run_id: str = "run_123") -> Run:
    timestamp = _timestamp()
    return Run(
        run_id=run_id,
        environment=EnvironmentRef(
            environment_id="env_helpdesk",
            environment_name="Northstar Helpdesk",
            environment_version="v1",
        ),
        scenario=ScenarioRef(
            scenario_id="scn_123",
            environment_id="env_helpdesk",
            scenario_name="travel-lockout",
            scenario_seed="seed-123",
        ),
        task=TaskRef(
            task_id="task_123",
            scenario_id="scn_123",
            task_kind="access_restoration",
            task_title="Restore employee access after travel lockout",
        ),
        status=RunStatus.PENDING,
        created_at=timestamp,
        updated_at=timestamp,
        current_step_index=0,
        active_agent_id="dummy-agent",
    )


def _run_created_event(run: Run, sequence: int = 0) -> RunEvent:
    return RunEvent(
        event_id=f"evt_created_{sequence}",
        run_id=run.run_id,
        sequence=sequence,
        occurred_at=_timestamp(),
        source=RunEventSource.WORKER,
        actor_type=ActorType.WORKER,
        correlation_id="corr_123",
        event_type=RunEventType.RUN_CREATED,
        payload=RunCreatedPayload(
            event_type=RunEventType.RUN_CREATED,
            run=run,
        ),
    )


def _tool_call_event(run: Run, sequence: int = 1) -> RunEvent:
    return RunEvent(
        event_id=f"evt_tool_{sequence}",
        run_id=run.run_id,
        sequence=sequence,
        occurred_at=_timestamp(),
        source=RunEventSource.WORKER,
        actor_type=ActorType.WORKER,
        correlation_id="corr_123",
        event_type=RunEventType.TOOL_CALL_RECORDED,
        payload=ToolCallRecordedPayload(
            event_type=RunEventType.TOOL_CALL_RECORDED,
            run_id=run.run_id,
            step_id=None,
            tool_call=ToolCall(
                tool_call_id="tool_001",
                tool_name="identity_api",
                action="lookup_account",
                arguments={"employee_id": "emp_123"},
                status=ToolCallStatus.SUCCEEDED,
                result={"account_state": "locked"},
            ),
        ),
    )


def _run_ready_event(run: Run, sequence: int = 1) -> RunEvent:
    return RunEvent(
        event_id=f"evt_ready_{sequence}",
        run_id=run.run_id,
        sequence=sequence,
        occurred_at=_timestamp(),
        source=RunEventSource.SYSTEM,
        actor_type=ActorType.SYSTEM,
        correlation_id="corr_123",
        event_type=RunEventType.RUN_READY,
        payload=RunReadyPayload(
            event_type=RunEventType.RUN_READY,
            run_id=run.run_id,
            status=RunStatus.READY,
        ),
    )


def _run_started_event(run: Run, sequence: int = 2) -> RunEvent:
    return RunEvent(
        event_id=f"evt_started_{sequence}",
        run_id=run.run_id,
        sequence=sequence,
        occurred_at=_timestamp(),
        source=RunEventSource.WORKER,
        actor_type=ActorType.WORKER,
        correlation_id="corr_123",
        event_type=RunEventType.RUN_STARTED,
        payload=RunStartedPayload(
            event_type=RunEventType.RUN_STARTED,
            run_id=run.run_id,
            status=RunStatus.RUNNING,
            started_at=_timestamp(),
        ),
    )


def _run_completed_event(
    run: Run,
    sequence: int = 4,
    final_status: RunStatus = RunStatus.SUCCEEDED,
) -> RunEvent:
    completed_payload: RunCompletedPayload = RunCompletedPayload(
        event_type=RunEventType.RUN_COMPLETED,
        run_id=run.run_id,
        final_status=cast(Any, final_status),
        completed_at=_timestamp(),
        grade_result=GradeResult(
            grade_id="grade_001",
            outcome=GradeOutcome.PASSED,
            score=1.0,
            summary="Dummy run completed successfully.",
        ),
    )
    return RunEvent(
        event_id=f"evt_completed_{sequence}",
        run_id=run.run_id,
        sequence=sequence,
        occurred_at=_timestamp(),
        source=RunEventSource.WORKER,
        actor_type=ActorType.WORKER,
        correlation_id="corr_123",
        event_type=RunEventType.RUN_COMPLETED,
        payload=completed_payload,
    )


def _artifact() -> Artifact:
    return Artifact(
        artifact_id="artifact_001",
        kind=ArtifactKind.LOG,
        uri="minio://atlas-artifacts/run_123/log.json",
        content_type="application/json",
        created_at=_timestamp(),
        size_bytes=128,
        metadata={"source": "integration-test"},
    )


def _connect() -> psycopg.Connection[dict[str, object]] | None:
    try:
        return open_run_store_connection(
            InfrastructureConfig.from_env().postgres_dsn(),
            autocommit=True,
        )
    except psycopg.OperationalError:
        return None


@pytest.fixture
def run_service() -> Generator[RunService, None, None]:
    conn = _connect()
    if conn is None:
        pytest.skip("local Postgres is not available")

    schema_name = f"test_run_store_{uuid.uuid4().hex[:8]}"
    migrations = discover_migrations(DEFAULT_MIGRATIONS_DIR)
    conn.execute(f'create schema "{schema_name}"')
    conn.execute(f'set search_path to "{schema_name}"')
    apply_migrations(conn, migrations)

    repository = RunRepository(conn)
    service = RunService(repository)

    try:
        yield service
    finally:
        with suppress(psycopg.Error):
            conn.execute(f'drop schema if exists "{schema_name}" cascade')
        conn.close()


def test_run_service_happy_path(run_service: RunService) -> None:
    run = _run()
    created = run_service.create_run(run)
    assert created == run

    assert run_service.get_run(run.run_id) == run
    assert run_service.list_runs() == [run]

    created_event = _run_created_event(run, sequence=0)
    ready_event = _run_ready_event(run, sequence=1)
    started_event = _run_started_event(run, sequence=2)
    tool_event = _tool_call_event(run, sequence=3)
    completed_event = _run_completed_event(run, sequence=4)
    appended_created = run_service.append_run_event(created_event)
    appended_ready = run_service.append_run_event(ready_event)
    appended_started = run_service.append_run_event(started_event)
    appended_tool = run_service.append_run_event(tool_event)
    appended_completed = run_service.append_run_event(completed_event)
    assert appended_created == created_event
    assert appended_ready == ready_event
    assert appended_started == started_event
    assert appended_tool == tool_event
    assert appended_completed == completed_event
    assert run_service.list_run_events(run.run_id) == [
        created_event,
        ready_event,
        started_event,
        tool_event,
        completed_event,
    ]

    artifact = _artifact()
    attached = run_service.attach_artifact(run_id=run.run_id, artifact=artifact)
    assert attached.run_id == run.run_id
    assert attached.step_id is None
    stored_artifact = run_service.list_run_artifacts(run.run_id)[0]
    assert stored_artifact.run_id == run.run_id
    assert stored_artifact.artifact_id == artifact.artifact_id

    finalized = run_service.get_run(run.run_id)
    completed_payload = cast(RunCompletedPayload, completed_event.payload)
    assert finalized.status == RunStatus.SUCCEEDED
    assert finalized.completed_at == completed_payload.completed_at
    assert finalized.grade_result == completed_payload.grade_result


def test_run_service_rejects_duplicate_run(run_service: RunService) -> None:
    run = _run()
    run_service.create_run(run)

    with pytest.raises(RunAlreadyExistsError):
        run_service.create_run(run)


def test_run_service_rejects_nonexistent_run_operations(run_service: RunService) -> None:
    with pytest.raises(RunNotFoundError):
        run_service.get_run("missing")

    with pytest.raises(RunNotFoundError):
        run_service.append_run_event(_run_created_event(_run("missing"), sequence=0))

    with pytest.raises(RunNotFoundError):
        run_service.attach_artifact(run_id="missing", artifact=_artifact())


def test_run_service_rejects_sequence_gaps_and_duplicates(run_service: RunService) -> None:
    run = _run()
    run_service.create_run(run)
    run_service.append_run_event(_run_created_event(run, sequence=0))
    run_service.append_run_event(_run_ready_event(run, sequence=1))
    run_service.append_run_event(_run_started_event(run, sequence=2))

    with pytest.raises(EventSequenceConflictError):
        run_service.append_run_event(_tool_call_event(run, sequence=4))

    run_service.append_run_event(_tool_call_event(run, sequence=3))
    with pytest.raises(EventSequenceConflictError):
        run_service.append_run_event(_tool_call_event(run, sequence=3))


def test_run_service_rejects_duplicate_artifact(run_service: RunService) -> None:
    run = _run()
    artifact = _artifact()
    run_service.create_run(run)
    run_service.attach_artifact(run_id=run.run_id, artifact=artifact)

    with pytest.raises(ArtifactAlreadyExistsError):
        run_service.attach_artifact(run_id=run.run_id, artifact=artifact)


def test_run_service_finalize_uses_state_machine(run_service: RunService) -> None:
    run = _run()
    run_service.create_run(run)
    run_service.append_run_event(_run_created_event(run, sequence=0))
    run_service.append_run_event(_run_ready_event(run, sequence=1))
    run_service.append_run_event(_run_started_event(run, sequence=2))

    finalized = run_service.finalize_run(
        run.run_id,
        RunFinalization(
            final_status=RunStatus.SUCCEEDED,
            completed_at=_timestamp(),
        ),
    )

    assert finalized.status == RunStatus.SUCCEEDED


def test_run_service_finalize_requires_existing_run(run_service: RunService) -> None:
    with pytest.raises(RunNotFoundError):
        run_service.finalize_run(
            "missing",
            RunFinalization(
                final_status=RunStatus.FAILED,
                completed_at=_timestamp(),
            ),
        )


def test_run_service_rejects_non_terminal_final_status(run_service: RunService) -> None:
    run = _run()
    run_service.create_run(run)

    with pytest.raises(InvalidRunFinalizationError):
        run_service.finalize_run(
            run.run_id,
            RunFinalization(
                final_status=RunStatus.RUNNING,
                completed_at=_timestamp(),
            ),
        )


def test_run_service_rejects_invalid_event_transition(run_service: RunService) -> None:
    run = _run()
    run_service.create_run(run)

    with pytest.raises(InvalidRunEventTransitionError):
        run_service.append_run_event(_run_started_event(run, sequence=0))
