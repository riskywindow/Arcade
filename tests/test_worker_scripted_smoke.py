from __future__ import annotations

import ast
from collections.abc import Generator
from contextlib import suppress
import uuid

import psycopg
import pytest
from psycopg.rows import dict_row

from atlas_core import (
    DEFAULT_MIGRATIONS_DIR,
    RunRepository,
    RunService,
    apply_migrations,
    discover_migrations,
)
from atlas_core.config import InfrastructureConfig, ServiceConfig
from atlas_worker.config import WorkerConfig
from atlas_worker.main import main
from atlas_worker.scripted_smoke import execute_scripted_smoke, execute_scripted_smoke_from_config


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

    schema_name = f"test_worker_smoke_{uuid.uuid4().hex[:8]}"
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


def test_execute_scripted_smoke_completes_two_seeded_tasks(
    isolated_worker_service: tuple[RunService, str],
) -> None:
    service, _ = isolated_worker_service

    result = execute_scripted_smoke(service, run_prefix="scripted-test")

    assert len(result.outcomes) == 2
    assert {outcome.scenario_id for outcome in result.outcomes} == {
        "travel-lockout-recovery",
        "shared-drive-access-request",
    }
    assert all(outcome.final_status.value == "succeeded" for outcome in result.outcomes)
    assert all(outcome.grade_result.outcome.value == "passed" for outcome in result.outcomes)
    assert all(outcome.event_count >= 12 for outcome in result.outcomes)
    assert all(outcome.artifact_count == 1 for outcome in result.outcomes)


def test_execute_scripted_smoke_from_config_uses_worker_path(
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
    )

    result = execute_scripted_smoke_from_config(
        config,
        schema_name=schema_name,
        run_prefix="scripted-config",
    )

    assert len(result.outcomes) == 2
    assert all(outcome.grade_result.outcome.value == "passed" for outcome in result.outcomes)


def test_worker_main_scripted_smoke_command(
    isolated_worker_service: tuple[RunService, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, schema_name = isolated_worker_service
    monkeypatch.setattr(
        "sys.argv",
        [
            "atlas-worker",
            "scripted-smoke",
            "--schema-name",
            schema_name,
            "--run-prefix",
            "scripted-cli",
        ],
    )

    main()

    output = ast.literal_eval(capsys.readouterr().out.strip())
    assert output["run_count"] == 2
    assert {item["scenario_id"] for item in output["outcomes"]} == {
        "travel-lockout-recovery",
        "shared-drive-access-request",
    }
    assert all(item["grade_outcome"] == "passed" for item in output["outcomes"])
