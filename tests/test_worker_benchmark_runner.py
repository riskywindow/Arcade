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
from atlas_worker.benchmark_runner import (
    execute_benchmark_catalog,
    execute_benchmark_catalog_from_config,
    get_benchmark_catalog,
)
from atlas_worker.config import WorkerConfig
from atlas_worker.main import main


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

    schema_name = f"test_worker_benchmark_{uuid.uuid4().hex[:8]}"
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


def test_helpdesk_v0_benchmark_catalog_is_small_and_explicit() -> None:
    catalog = get_benchmark_catalog("helpdesk-v0")

    assert catalog.catalog_id == "helpdesk-v0"
    assert [entry.entry_id for entry in catalog.entries] == [
        "travel-lockout-recovery",
        "shared-drive-access-request",
    ]
    assert all(entry.runner_kind.value == "scripted_helpdesk" for entry in catalog.entries)


def test_execute_benchmark_catalog_persists_seeded_runs_and_scores(
    isolated_worker_service: tuple[RunService, str],
) -> None:
    service, _ = isolated_worker_service
    catalog = get_benchmark_catalog("helpdesk-v0")

    result = execute_benchmark_catalog(
        service,
        catalog=catalog,
        benchmark_run_id="benchmark-test-001",
    )

    assert result.benchmark_run_id == "benchmark-test-001"
    assert result.aggregate.total_runs == 2
    assert result.aggregate.passed_runs == 2
    assert result.aggregate.failed_runs == 0
    assert len(result.items) == 2
    assert {item.entry_id for item in result.items} == {
        "travel-lockout-recovery",
        "shared-drive-access-request",
    }
    assert all(item.score_summary.passed is True for item in result.items)
    assert all(service.get_run(item.run_id) is not None for item in result.items)


def test_execute_benchmark_catalog_from_config_uses_worker_path(
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

    result = execute_benchmark_catalog_from_config(
        config,
        catalog_id="helpdesk-v0",
        benchmark_run_id="benchmark-config-001",
        schema_name=schema_name,
    )

    assert result.aggregate.total_runs == 2
    assert all(item.score_summary.passed is True for item in result.items)


def test_worker_main_benchmark_run_command(
    isolated_worker_service: tuple[RunService, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, schema_name = isolated_worker_service
    monkeypatch.setattr(
        "sys.argv",
        [
            "atlas-worker",
            "benchmark-run",
            "--schema-name",
            schema_name,
            "--catalog-id",
            "helpdesk-v0",
            "--benchmark-run-id",
            "benchmark-cli-001",
        ],
    )

    main()

    output = ast.literal_eval(capsys.readouterr().out.strip())
    assert output["benchmark_run_id"] == "benchmark-cli-001"
    assert output["catalog_id"] == "helpdesk-v0"
    assert output["run_count"] == 2
    assert output["passed_runs"] == 2
    assert {item["scenario_id"] for item in output["items"]} == {
        "travel-lockout-recovery",
        "shared-drive-access-request",
    }
