from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime
import uuid
from collections.abc import Generator
from typing import Any, cast

import psycopg
import pytest
from fastapi.testclient import TestClient

from atlas_api.app import create_app
from atlas_api.config import ApiConfig
from atlas_core import (
    ActorType,
    Artifact,
    ArtifactKind,
    DEFAULT_MIGRATIONS_DIR,
    EnvironmentRef,
    Run,
    RunCompletedPayload,
    RunCreatedPayload,
    RunEvent,
    RunEventSource,
    RunEventType,
    RunReadyPayload,
    RunRepository,
    RunService,
    RunStartedPayload,
    RunStatus,
    RunStepCreatedPayload,
    ScenarioRef,
    ServiceConfig,
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


def _connect() -> psycopg.Connection[dict[str, object]] | None:
    try:
        return open_run_store_connection(
            InfrastructureConfig.from_env().postgres_dsn(),
            autocommit=True,
        )
    except psycopg.OperationalError:
        return None


def _run_service(schema_name: str) -> tuple[RunService, psycopg.Connection[dict[str, object]]]:
    conn = open_run_store_connection(
        InfrastructureConfig.from_env().postgres_dsn(),
        autocommit=True,
    )
    conn.execute("select set_config('search_path', %s, false)", (schema_name,))
    return RunService(RunRepository(conn)), conn


def _run(run_id: str) -> Run:
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
        active_agent_id="dummy-agent",
    )


def _event(run: Run, event_type: RunEventType, sequence: int) -> RunEvent:
    payload: (
        RunCreatedPayload
        | RunReadyPayload
        | RunStartedPayload
        | RunCompletedPayload
        | ToolCallRecordedPayload
        | RunStepCreatedPayload
    )
    if event_type == RunEventType.RUN_CREATED:
        payload = RunCreatedPayload(
            event_type=RunEventType.RUN_CREATED,
            run=run,
        )
    elif event_type == RunEventType.RUN_READY:
        payload = RunReadyPayload(
            event_type=RunEventType.RUN_READY,
            run_id=run.run_id,
            status=RunStatus.READY,
        )
    elif event_type == RunEventType.RUN_STARTED:
        payload = RunStartedPayload(
            event_type=RunEventType.RUN_STARTED,
            run_id=run.run_id,
            status=RunStatus.RUNNING,
            started_at=_timestamp(),
        )
    elif event_type == RunEventType.RUN_COMPLETED:
        payload = RunCompletedPayload(
            event_type=RunEventType.RUN_COMPLETED,
            run_id=run.run_id,
            final_status=RunStatus.SUCCEEDED,
            completed_at=_timestamp(),
        )
    else:
        payload = ToolCallRecordedPayload(
            event_type=RunEventType.TOOL_CALL_RECORDED,
            run_id=run.run_id,
            tool_call=ToolCall(
                tool_call_id="tool_001",
                tool_name="identity_api",
                action="lookup_account",
                arguments={"employee_id": "emp_123"},
                status=ToolCallStatus.SUCCEEDED,
                result={"account_state": "locked"},
            ),
        )

    return RunEvent(
        event_id=f"evt_{sequence}",
        run_id=run.run_id,
        sequence=sequence,
        occurred_at=_timestamp(),
        source=RunEventSource.WORKER,
        actor_type=ActorType.WORKER,
        event_type=event_type,
        payload=payload,
    )


@pytest.fixture
def api_client() -> Generator[TestClient, None, None]:
    conn = _connect()
    if conn is None:
        pytest.skip("local Postgres is not available")

    schema_name = f"test_run_api_{uuid.uuid4().hex[:8]}"
    conn.execute(f'create schema "{schema_name}"')
    conn.execute(f'set search_path to "{schema_name}"')
    apply_migrations(conn, discover_migrations(DEFAULT_MIGRATIONS_DIR))

    config = ApiConfig(
        service=ServiceConfig(
            service_name="atlas-api",
            environment="test",
            host="127.0.0.1",
            port=8000,
            log_level="INFO",
            reload=False,
        ),
        infrastructure=InfrastructureConfig.from_env(),
    )
    app = create_app(config)
    app.state.database_schema = schema_name
    client = TestClient(app)

    try:
        yield client
    finally:
        with suppress(psycopg.Error):
            conn.execute(f'drop schema if exists "{schema_name}" cascade')
        conn.close()


def test_run_api_create_list_get_and_events(api_client: TestClient) -> None:
    create_response = api_client.post(
        "/runs",
        json={
            "environment": {
                "environmentId": "env_helpdesk",
                "environmentName": "Northstar Helpdesk",
                "environmentVersion": "v1",
            },
            "scenario": {
                "scenarioId": "scn_123",
                "environmentId": "env_helpdesk",
                "scenarioName": "travel-lockout",
                "scenarioSeed": "seed-123",
            },
            "task": {
                "taskId": "task_123",
                "scenarioId": "scn_123",
                "taskKind": "access_restoration",
                "taskTitle": "Restore employee access after travel lockout",
            },
            "activeAgentId": "dummy-agent",
        },
    )

    assert create_response.status_code == 201
    run_payload = create_response.json()["run"]
    run_id = run_payload["runId"]
    assert run_payload["status"] == "pending"

    schema_name = cast(Any, api_client.app).state.database_schema
    service, service_conn = _run_service(schema_name)
    try:
        run = service.get_run(run_id)
        service.append_run_event(_event(run, RunEventType.RUN_CREATED, 0))
        service.append_run_event(_event(run, RunEventType.RUN_READY, 1))
        service.append_run_event(_event(run, RunEventType.RUN_STARTED, 2))
        service.append_run_event(_event(run, RunEventType.TOOL_CALL_RECORDED, 3))
        service.attach_artifact(
            run_id=run_id,
            artifact=Artifact(
                artifact_id="artifact_001",
                kind=ArtifactKind.LOG,
                uri="minio://atlas-artifacts/run_123/log.json",
                content_type="application/json",
                created_at=_timestamp(),
                metadata={"source": "api-test"},
            ),
        )
    finally:
        service_conn.close()

    list_response = api_client.get("/runs")
    assert list_response.status_code == 200
    assert [item["runId"] for item in list_response.json()["runs"]] == [run_id]

    get_response = api_client.get(f"/runs/{run_id}")
    assert get_response.status_code == 200
    assert get_response.json()["run"]["runId"] == run_id

    events_response = api_client.get(f"/runs/{run_id}/events")
    assert events_response.status_code == 200
    assert events_response.json()["runId"] == run_id
    assert events_response.json()["events"][0]["schemaVersion"] == 1
    assert events_response.json()["events"][0]["payload"]["schemaVersion"] == 1
    assert [item["eventType"] for item in events_response.json()["events"]] == [
        "run.created",
        "run.ready",
        "run.started",
        "tool_call.recorded",
    ]

    artifacts_response = api_client.get(f"/runs/{run_id}/artifacts")
    assert artifacts_response.status_code == 200
    assert artifacts_response.json()["artifacts"][0]["artifactId"] == "artifact_001"
    assert artifacts_response.json()["artifacts"][0]["runId"] == run_id
    assert artifacts_response.json()["artifacts"][0]["schemaVersion"] == 1


def test_run_api_returns_404_for_missing_run(api_client: TestClient) -> None:
    response = api_client.get("/runs/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "run missing does not exist"


def test_run_api_validates_request_shape(api_client: TestClient) -> None:
    response = api_client.post(
        "/runs",
        json={
            "environment": {
                "environmentId": "env_helpdesk",
                "environmentName": "Northstar Helpdesk",
            },
            "scenario": {
                "scenarioId": "scn_123",
                "environmentId": "env_other",
                "scenarioName": "travel-lockout",
                "scenarioSeed": "seed-123",
            },
            "task": {
                "taskId": "task_123",
                "scenarioId": "scn_123",
                "taskKind": "access_restoration",
                "taskTitle": "Restore employee access after travel lockout",
            },
        },
    )

    assert response.status_code == 422
