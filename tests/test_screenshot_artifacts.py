from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime
from collections.abc import Generator
from pathlib import Path
import uuid

import psycopg
import pytest
from psycopg.rows import dict_row
from fastapi.testclient import TestClient

from atlas_api.app import create_app
from atlas_api.config import ApiConfig
from atlas_core import (
    ActorType,
    ArtifactKind,
    DEFAULT_MIGRATIONS_DIR,
    EnvironmentRef,
    LocalArtifactStore,
    Run,
    RunCreatedPayload,
    RunEvent,
    RunEventSource,
    RunEventType,
    RunRepository,
    RunService,
    RunStatus,
    ScenarioRef,
    TaskRef,
    ToolRequest,
    ToolResultOutcome,
    apply_migrations,
    discover_migrations,
)
from atlas_core.config import InfrastructureConfig, ServiceConfig
from atlas_worker import ScreenshotToolExecutor
from browser_runner import BrowserCommand, BrowserObservation, BrowserScreenshot


class _FakeScreenshotRunner:
    def run(self, command: BrowserCommand) -> BrowserObservation:
        return BrowserObservation(
            current_url="http://127.0.0.1:3000/internal/helpdesk",
            title=f"Observed {command.action.value}",
            page_summary="Helpdesk Queue",
            extracted_text="Helpdesk Queue",
            visible_test_ids=("nav-link-helpdesk",),
        )

    def capture_screenshot(self, label: str | None = None) -> BrowserScreenshot:
        return BrowserScreenshot(
            current_url="http://127.0.0.1:3000/internal/helpdesk",
            title="Helpdesk Queue",
            screenshot_bytes=b"\x89PNG\r\nphase4",
            default_filename=f"{label or 'browser'}.png",
        )

    def close(self) -> None:
        return None


def _timestamp() -> datetime:
    return datetime(2026, 3, 16, 12, 0, tzinfo=UTC)


def _connect() -> psycopg.Connection[dict[str, object]] | None:
    dsn = InfrastructureConfig.from_env().postgres_dsn()
    try:
        return psycopg.connect(dsn, autocommit=True, row_factory=dict_row)
    except psycopg.OperationalError:
        return None


def _build_run(run_id: str) -> Run:
    timestamp = _timestamp()
    return Run(
        run_id=run_id,
        environment=EnvironmentRef(
            environment_id="env_helpdesk",
            environment_name="Northstar Helpdesk",
            environment_version="v1",
        ),
        scenario=ScenarioRef(
            scenario_id="mfa-reenrollment-device-loss",
            environment_id="env_helpdesk",
            scenario_name="MFA Re-Enrollment After Device Loss",
            scenario_seed="seed-phase4-demo",
        ),
        task=TaskRef(
            task_id="task_mfa_reenrollment_device_loss",
            scenario_id="mfa-reenrollment-device-loss",
            task_kind="access_restoration",
            task_title="Restore access after device loss",
        ),
        status=RunStatus.PENDING,
        created_at=timestamp,
        updated_at=timestamp,
        active_agent_id="agent_phase4",
    )


@pytest.fixture
def screenshot_api_client(tmp_path: Path) -> Generator[tuple[TestClient, RunService, Path], None, None]:
    conn = _connect()
    if conn is None:
        pytest.skip("local Postgres is not available")

    schema_name = f"test_screenshot_artifacts_{uuid.uuid4().hex[:8]}"
    conn.execute(f'create schema "{schema_name}"')
    conn.execute("select set_config('search_path', %s, false)", (schema_name,))
    apply_migrations(conn, discover_migrations(DEFAULT_MIGRATIONS_DIR))

    service = RunService(RunRepository(conn))
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
        yield client, service, tmp_path / "artifacts"
    finally:
        with suppress(psycopg.Error):
            conn.execute(f'drop schema if exists "{schema_name}" cascade')
        conn.close()


def test_screenshot_executor_persists_artifact_and_api_lists_it(
    screenshot_api_client: tuple[TestClient, RunService, Path],
) -> None:
    client, run_service, artifact_dir = screenshot_api_client
    run = _build_run("run_screenshot_001")
    run_service.create_run(run)
    run_service.append_run_event(
        RunEvent(
            event_id="evt_created_001",
            run_id=run.run_id,
            sequence=0,
            occurred_at=_timestamp(),
            source=RunEventSource.WORKER,
            actor_type=ActorType.WORKER,
            event_type=RunEventType.RUN_CREATED,
            payload=RunCreatedPayload(
                event_type=RunEventType.RUN_CREATED,
                run=run,
            ),
        )
    )

    executor = ScreenshotToolExecutor(
        run_service=run_service,
        artifact_store=LocalArtifactStore(artifact_dir),
        runner=_FakeScreenshotRunner(),
    )
    result = executor.execute(
        ToolRequest(
            request_id="toolreq_screenshot_001",
            tool_name="screenshot_capture",
            arguments={"scope": "page", "label": "helpdesk-queue"},
            metadata={"run_id": run.run_id, "step_id": "run_screenshot_001-step-001"},
        )
    )

    assert result.outcome == ToolResultOutcome.SUCCESS
    artifact_id = result.artifact_ids[0]

    artifacts = run_service.list_run_artifacts(run.run_id)
    assert len(artifacts) == 1
    assert artifacts[0].artifact_id == artifact_id
    assert artifacts[0].kind == ArtifactKind.SCREENSHOT
    assert Path(artifacts[0].uri).exists()

    events = run_service.list_run_events(run.run_id)
    assert events[-1].event_type == RunEventType.ARTIFACT_ATTACHED

    response = client.get(f"/runs/{run.run_id}/artifacts")
    assert response.status_code == 200
    payload = response.json()
    assert payload["artifacts"][0]["artifactId"] == artifact_id
    assert payload["artifacts"][0]["kind"] == "screenshot"

    content_response = client.get(f"/runs/{run.run_id}/artifacts/{artifact_id}/content")
    assert content_response.status_code == 200
    assert content_response.headers["content-type"] == "image/png"
    assert content_response.content == b"\x89PNG\r\nphase4"
