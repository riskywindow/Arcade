from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from atlas_core.domain import AtlasModel, CURRENT_SCHEMA_VERSION
from atlas_core.evaluation import RunScoreSummary


class BenchmarkRunnerKind(StrEnum):
    SCRIPTED_HELPDESK = "scripted_helpdesk"


class BenchmarkCatalogEntry(AtlasModel):
    entry_id: str
    scenario_id: str
    scenario_name: str
    task_id: str
    task_title: str
    seed: str
    runner_kind: BenchmarkRunnerKind
    tags: tuple[str, ...] = ()


class BenchmarkCatalog(AtlasModel):
    schema_version: int = Field(default=CURRENT_SCHEMA_VERSION, ge=1)
    catalog_id: str
    title: str
    description: str
    environment_id: str
    entries: tuple[BenchmarkCatalogEntry, ...]


class BenchmarkRunItemResult(AtlasModel):
    entry_id: str
    run_id: str
    scenario_id: str
    task_id: str
    task_title: str
    final_status: str
    score_summary: RunScoreSummary


class BenchmarkRunAggregate(AtlasModel):
    total_runs: int = Field(ge=0)
    passed_runs: int = Field(ge=0)
    failed_runs: int = Field(ge=0)
    average_score: float | None = Field(default=None, ge=0.0, le=1.0)


class BenchmarkRunResult(AtlasModel):
    schema_version: int = Field(default=CURRENT_SCHEMA_VERSION, ge=1)
    benchmark_run_id: str
    catalog_id: str
    seed: str
    started_at: datetime
    completed_at: datetime
    items: tuple[BenchmarkRunItemResult, ...]
    aggregate: BenchmarkRunAggregate


def benchmark_entry_run_id(benchmark_run_id: str, entry_id: str) -> str:
    return f"{benchmark_run_id}--{entry_id}"


def build_benchmark_run_result(
    *,
    benchmark_run_id: str,
    catalog_id: str,
    seed: str,
    started_at: datetime,
    completed_at: datetime,
    items: tuple[BenchmarkRunItemResult, ...],
) -> BenchmarkRunResult:
    return BenchmarkRunResult(
        benchmark_run_id=benchmark_run_id,
        catalog_id=catalog_id,
        seed=seed,
        started_at=started_at,
        completed_at=completed_at,
        items=items,
        aggregate=build_benchmark_aggregate(items),
    )


def build_benchmark_aggregate(
    items: tuple[BenchmarkRunItemResult, ...],
) -> BenchmarkRunAggregate:
    total_runs = len(items)
    passed_runs = sum(1 for item in items if item.score_summary.passed)
    failed_runs = total_runs - passed_runs
    scored_items = [item.score_summary.score for item in items if item.score_summary.score is not None]
    average_score = (
        sum(scored_items) / len(scored_items)
        if scored_items
        else None
    )
    return BenchmarkRunAggregate(
        total_runs=total_runs,
        passed_runs=passed_runs,
        failed_runs=failed_runs,
        average_score=average_score,
    )
