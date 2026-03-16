from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime
import uuid

import psycopg
import pytest
from psycopg.rows import dict_row

from atlas_core import DEFAULT_MIGRATIONS_DIR, InfrastructureConfig, discover_migrations
from atlas_core.db import apply_migrations, rollback_migrations


def _connect_for_test() -> psycopg.Connection[dict[str, object]] | None:
    dsn = InfrastructureConfig.from_env().postgres_dsn()
    try:
        return psycopg.connect(dsn, row_factory=dict_row)
    except psycopg.OperationalError:
        return None


def _table_exists(conn: psycopg.Connection[dict[str, object]], table_name: str) -> bool:
    result = conn.execute(
        "select to_regclass(%s) as table_name",
        (table_name,),
    ).fetchone()
    return bool(result and result["table_name"] == table_name)


def test_run_spine_migrations_store_and_order_events() -> None:
    conn = _connect_for_test()
    if conn is None:
        pytest.skip("local Postgres is not available")

    schema_name = f"test_run_spine_{uuid.uuid4().hex[:8]}"
    migrations = discover_migrations(DEFAULT_MIGRATIONS_DIR)
    timestamp = datetime(2026, 3, 15, 12, 0, tzinfo=UTC)

    conn.autocommit = True
    try:
        conn.execute(f'create schema "{schema_name}"')
        conn.execute(f'set search_path to "{schema_name}"')

        applied = apply_migrations(conn, migrations)
        assert applied == ["0001"]
        assert _table_exists(conn, "runs")
        assert _table_exists(conn, "run_events")
        assert _table_exists(conn, "run_artifacts")

        conn.execute(
            """
            insert into runs (
                run_id,
                environment_id,
                environment_name,
                environment_version,
                scenario_id,
                scenario_name,
                scenario_seed,
                task_id,
                task_kind,
                task_title,
                status,
                created_at,
                updated_at,
                current_step_index,
                active_agent_id,
                grade_result
            )
            values (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb
            )
            """,
            (
                "run_123",
                "env_helpdesk",
                "Northstar Helpdesk",
                "v1",
                "scn_123",
                "travel-lockout",
                "seed-123",
                "task_123",
                "access_restoration",
                "Restore employee access after travel lockout",
                "pending",
                timestamp,
                timestamp,
                0,
                "dummy-agent",
                '{"outcome":"not_graded","summary":"pending"}',
            ),
        )
        conn.execute(
            """
            insert into run_events (
                event_id,
                run_id,
                sequence,
                occurred_at,
                source,
                actor_type,
                correlation_id,
                event_type,
                payload
            )
            values
                (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb),
                (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            """,
            (
                "evt_001",
                "run_123",
                0,
                timestamp,
                "worker",
                "worker",
                "corr_123",
                "run.created",
                '{"event_type":"run.created"}',
                "evt_002",
                "run_123",
                1,
                timestamp,
                "worker",
                "worker",
                "corr_123",
                "run.started",
                '{"event_type":"run.started"}',
            ),
        )
        conn.execute(
            """
            insert into run_artifacts (
                artifact_id,
                run_id,
                step_id,
                kind,
                uri,
                content_type,
                created_at,
                sha256,
                size_bytes,
                metadata
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            """,
            (
                "artifact_001",
                "run_123",
                None,
                "log",
                "minio://atlas-artifacts/run_123/log.json",
                "application/json",
                timestamp,
                None,
                128,
                '{"source":"integration-test"}',
            ),
        )

        rows = conn.execute(
            """
            select event_id, sequence
            from run_events
            where run_id = %s
            order by sequence asc
            """,
            ("run_123",),
        ).fetchall()
        assert rows == [
            {"event_id": "evt_001", "sequence": 0},
            {"event_id": "evt_002", "sequence": 1},
        ]

        with pytest.raises(psycopg.errors.UniqueViolation):
            conn.execute(
                """
                insert into run_events (
                    event_id,
                    run_id,
                    sequence,
                    occurred_at,
                    source,
                    actor_type,
                    correlation_id,
                    event_type,
                    payload
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    "evt_003",
                    "run_123",
                    1,
                    timestamp,
                    "worker",
                    "worker",
                    "corr_123",
                    "tool_call.recorded",
                    '{"event_type":"tool_call.recorded"}',
                ),
            )

        rolled_back = rollback_migrations(conn, migrations, steps=1)
        assert rolled_back == ["0001"]
        assert not _table_exists(conn, "runs")
    finally:
        with suppress(psycopg.Error):
            conn.execute(f'drop schema if exists "{schema_name}" cascade')
        conn.close()


def test_discover_migrations_requires_up_and_down_pairs(tmp_path) -> None:
    up_path = tmp_path / "0001_example.up.sql"
    up_path.write_text("select 1;")

    with pytest.raises(ValueError):
        discover_migrations(tmp_path)


def test_cleanup_safely_ignores_missing_schema() -> None:
    conn = _connect_for_test()
    if conn is None:
        pytest.skip("local Postgres is not available")

    with conn:
        with suppress(psycopg.Error):
            conn.execute('drop schema if exists "missing_schema" cascade')
