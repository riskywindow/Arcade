from __future__ import annotations

from atlas_core import (
    BenchmarkCatalog,
    BenchmarkRunItemResult,
    BenchmarkRunResult,
    BenchmarkRunnerKind,
    RunRepository,
    RunService,
    benchmark_entry_run_id,
    build_benchmark_run_result,
    build_run_score_summary,
    open_run_store_connection,
)
from atlas_env_helpdesk import get_benchmark_catalog_v0
from atlas_worker.config import WorkerConfig
from atlas_worker.scripted_smoke import execute_scripted_scenario


def get_benchmark_catalog(catalog_id: str, *, seed: str = "seed-phase3-demo") -> BenchmarkCatalog:
    if catalog_id == "helpdesk-v0":
        return get_benchmark_catalog_v0(seed=seed)
    raise KeyError(f"unknown benchmark catalog: {catalog_id}")


def execute_benchmark_catalog(
    run_service: RunService,
    *,
    catalog: BenchmarkCatalog,
    benchmark_run_id: str,
) -> BenchmarkRunResult:
    items: list[BenchmarkRunItemResult] = []
    run_start_times = []
    run_end_times = []

    for entry in catalog.entries:
        run_id = benchmark_entry_run_id(benchmark_run_id, entry.entry_id)
        if entry.runner_kind != BenchmarkRunnerKind.SCRIPTED_HELPDESK:
            raise KeyError(f"unsupported benchmark runner kind: {entry.runner_kind}")
        execute_scripted_scenario(
            run_service,
            scenario_id=entry.scenario_id,
            seed=entry.seed,
            run_id=run_id,
        )
        run = run_service.get_run(run_id)
        events = run_service.list_run_events(run_id)
        artifacts = run_service.list_run_artifacts(run_id)
        score_summary = build_run_score_summary(run, events, artifacts)
        run_start_times.append(run.created_at)
        run_end_times.append(run.completed_at or run.updated_at)
        items.append(
            BenchmarkRunItemResult(
                entry_id=entry.entry_id,
                run_id=run_id,
                scenario_id=entry.scenario_id,
                task_id=entry.task_id,
                task_title=entry.task_title,
                final_status=run.status.value,
                score_summary=score_summary,
            )
        )

    return build_benchmark_run_result(
        benchmark_run_id=benchmark_run_id,
        catalog_id=catalog.catalog_id,
        seed=catalog.entries[0].seed if catalog.entries else "seed-phase3-demo",
        started_at=min(run_start_times),
        completed_at=max(run_end_times),
        items=tuple(items),
    )


def execute_benchmark_catalog_from_config(
    config: WorkerConfig,
    *,
    catalog_id: str,
    benchmark_run_id: str,
    seed: str = "seed-phase3-demo",
    schema_name: str | None = None,
) -> BenchmarkRunResult:
    conn = open_run_store_connection(config.infrastructure.postgres_dsn(), autocommit=True)
    if schema_name:
        conn.execute("select set_config('search_path', %s, false)", (schema_name,))
    try:
        service = RunService(RunRepository(conn))
        catalog = get_benchmark_catalog(catalog_id, seed=seed)
        return execute_benchmark_catalog(
            service,
            catalog=catalog,
            benchmark_run_id=benchmark_run_id,
        )
    finally:
        conn.close()
