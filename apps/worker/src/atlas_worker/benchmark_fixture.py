from __future__ import annotations

from datetime import UTC, timedelta
from pathlib import Path

from atlas_core import (
    ActorType,
    ApprovalRequestRef,
    ApprovalRequestStatus,
    ApprovalResolvedPayload,
    BenchmarkCatalog,
    BenchmarkRunComparison,
    BenchmarkRunItemResult,
    BenchmarkRunResult,
    GradeOutcome,
    GradeResult,
    PolicyDecision,
    PolicyDecisionOutcome,
    RunStatus,
    RunEvent,
    RunEventSource,
    RunEventType,
    RunRepository,
    RunService,
    ToolCall,
    ToolCallRecordedPayload,
    ToolCallStatus,
    benchmark_entry_run_id,
    build_benchmark_run_result,
    build_run_score_summary,
    compare_benchmark_runs,
    open_run_store_connection,
)
from atlas_core.domain import AtlasModel
from atlas_worker.benchmark_runner import execute_benchmark_catalog, get_benchmark_catalog
from atlas_worker.config import WorkerConfig

DEFAULT_BASELINE_BENCHMARK_RUN_ID = "benchmark-helpdesk-v0-baseline"
DEFAULT_CANDIDATE_BENCHMARK_RUN_ID = "benchmark-helpdesk-v0-regressed"
DEFAULT_SAMPLE_REPORT_PATH = Path("docs/demos/phase6-benchmark-sample-report.md")
FIXTURE_REGRESSION_ENTRY_ID = "travel-lockout-recovery"


class BenchmarkFixtureResult(AtlasModel):
    catalog_id: str
    baseline: BenchmarkRunResult
    candidate: BenchmarkRunResult
    comparison: BenchmarkRunComparison
    sample_report_path: str


def execute_benchmark_fixture(
    run_service: RunService,
    *,
    catalog_id: str = "helpdesk-v0",
    baseline_benchmark_run_id: str = DEFAULT_BASELINE_BENCHMARK_RUN_ID,
    candidate_benchmark_run_id: str = DEFAULT_CANDIDATE_BENCHMARK_RUN_ID,
    sample_report_path: str | Path = DEFAULT_SAMPLE_REPORT_PATH,
) -> BenchmarkFixtureResult:
    catalog = get_benchmark_catalog(catalog_id)
    baseline = execute_benchmark_catalog(
        run_service,
        catalog=catalog,
        benchmark_run_id=baseline_benchmark_run_id,
    )
    execute_benchmark_catalog(
        run_service,
        catalog=catalog,
        benchmark_run_id=candidate_benchmark_run_id,
    )
    _apply_regression_fixture(run_service, candidate_benchmark_run_id)
    candidate = load_benchmark_run_result(
        run_service,
        catalog=catalog,
        benchmark_run_id=candidate_benchmark_run_id,
    )
    comparison = compare_benchmark_runs(baseline, candidate)
    report_path = Path(sample_report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        render_benchmark_sample_report(
            baseline=baseline,
            candidate=candidate,
            comparison=comparison,
        ),
        encoding="utf-8",
    )
    return BenchmarkFixtureResult(
        catalog_id=catalog_id,
        baseline=baseline,
        candidate=candidate,
        comparison=comparison,
        sample_report_path=str(report_path),
    )


def execute_benchmark_fixture_from_config(
    config: WorkerConfig,
    *,
    catalog_id: str = "helpdesk-v0",
    baseline_benchmark_run_id: str = DEFAULT_BASELINE_BENCHMARK_RUN_ID,
    candidate_benchmark_run_id: str = DEFAULT_CANDIDATE_BENCHMARK_RUN_ID,
    sample_report_path: str | Path = DEFAULT_SAMPLE_REPORT_PATH,
    schema_name: str | None = None,
) -> BenchmarkFixtureResult:
    conn = open_run_store_connection(config.infrastructure.postgres_dsn(), autocommit=True)
    if schema_name:
        conn.execute("select set_config('search_path', %s, false)", (schema_name,))
    try:
        service = RunService(RunRepository(conn))
        return execute_benchmark_fixture(
            service,
            catalog_id=catalog_id,
            baseline_benchmark_run_id=baseline_benchmark_run_id,
            candidate_benchmark_run_id=candidate_benchmark_run_id,
            sample_report_path=sample_report_path,
        )
    finally:
        conn.close()


def load_benchmark_run_result(
    run_service: RunService,
    *,
    catalog: BenchmarkCatalog,
    benchmark_run_id: str,
) -> BenchmarkRunResult:
    items: list[BenchmarkRunItemResult] = []
    started_at = None
    completed_at = None
    seed = None

    for entry in catalog.entries:
        run_id = benchmark_entry_run_id(benchmark_run_id, entry.entry_id)
        run = run_service.get_run(run_id)
        events = run_service.list_run_events(run_id)
        artifacts = run_service.list_run_artifacts(run_id)
        score_summary = build_run_score_summary(run, events, artifacts)
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
        started_at = run.created_at if started_at is None else min(started_at, run.created_at)
        run_completed_at = run.completed_at or run.updated_at
        completed_at = (
            run_completed_at if completed_at is None else max(completed_at, run_completed_at)
        )
        seed = run.scenario.scenario_seed if seed is None else seed

    return build_benchmark_run_result(
        benchmark_run_id=benchmark_run_id,
        catalog_id=catalog.catalog_id,
        seed=seed or "seed-phase3-demo",
        started_at=started_at,
        completed_at=completed_at,
        items=tuple(items),
    )


def render_benchmark_sample_report(
    *,
    baseline: BenchmarkRunResult,
    candidate: BenchmarkRunResult,
    comparison: BenchmarkRunComparison,
) -> str:
    lines = [
        "# Phase 6 Sample Benchmark Report",
        "",
        "This report is generated from stored run score summaries and the pairwise",
        "benchmark comparison contract. It is intentionally narrow: pass rate, score,",
        "policy friction, and per-scenario interpretation.",
        "",
        f"- Catalog: `{candidate.catalog_id}`",
        f"- Baseline benchmark: `{baseline.benchmark_run_id}`",
        f"- Candidate benchmark: `{candidate.benchmark_run_id}`",
        f"- Comparison outcome: `{comparison.outcome}`",
        "",
        "## Candidate Summary",
        "",
        f"- Passed runs: `{candidate.aggregate.passed_runs}/{candidate.aggregate.total_runs}`",
        f"- Failed runs: `{candidate.aggregate.failed_runs}`",
        f"- Average score: `{_format_score(candidate.aggregate.average_score)}`",
        f"- Approval count: `{sum(item.score_summary.approval_counts.total for item in candidate.items)}`",
        f"- Denied policy count: `{sum(item.score_summary.policy_counts.deny for item in candidate.items)}`",
        "",
        "## Regression Signals",
        "",
    ]
    if comparison.regressions:
        lines.extend(f"- {regression}" for regression in comparison.regressions[:5])
    else:
        lines.append("- No tracked regressions were detected.")
    lines.extend(
        [
            "",
            "## Scenario Scorecard",
            "",
            "| Scenario | Outcome | Score | Approvals | Denies | Interpretation |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    item_comparisons = {item.entry_id: item for item in comparison.item_comparisons}
    for item in candidate.items:
        item_comparison = item_comparisons.get(item.entry_id)
        lines.append(
            "| "
            f"{item.task_title} | "
            f"{'passed' if item.score_summary.passed else 'failed'} | "
            f"{_format_score(item.score_summary.score)} | "
            f"{item.score_summary.approval_counts.total} | "
            f"{item.score_summary.policy_counts.deny} | "
            f"{item_comparison.comparison.summary if item_comparison else 'No baseline comparison attached.'} |"
        )
    lines.extend(
        [
            "",
            "## Measurement Notes",
            "",
            "- These numbers are derived from `RunScoreSummary`, not raw grader internals.",
            "- The regressed candidate is a deterministic fixture; it intentionally injects a failed helpdesk path, one extra approval, and one denied action.",
            "- Timing is wall-clock duration from the stored run summary and does not separate active time from approval wait time.",
            "",
        ]
    )
    return "\n".join(lines)


def _apply_regression_fixture(run_service: RunService, benchmark_run_id: str) -> None:
    repository: RunRepository = run_service._repository  # type: ignore[attr-defined]
    run_id = benchmark_entry_run_id(benchmark_run_id, FIXTURE_REGRESSION_ENTRY_ID)
    run = run_service.get_run(run_id)
    occurred_at = (run.completed_at or run.updated_at).astimezone(UTC)

    repository.append_run_event(
        RunEvent(
            event_id=f"{run_id}-fixture-deny",
            run_id=run_id,
            sequence=repository.next_event_sequence(run_id),
            occurred_at=occurred_at + timedelta(seconds=1),
            source=RunEventSource.BASTION,
            actor_type=ActorType.BASTION,
            correlation_id="fixture-deny",
            event_type=RunEventType.TOOL_CALL_RECORDED,
            payload=ToolCallRecordedPayload(
                event_type=RunEventType.TOOL_CALL_RECORDED,
                run_id=run_id,
                step_id=None,
                tool_call=ToolCall(
                    tool_call_id="tool-fixture-deny",
                    tool_name="identity_api",
                    action="disable_mfa",
                    arguments={"employee_id": "emp_123"},
                    status=ToolCallStatus.FAILED,
                    error_message="denied by benchmark fixture",
                ),
                policy_decision=PolicyDecision(
                    decision_id="policy-fixture-deny",
                    outcome=PolicyDecisionOutcome.DENY,
                    action_type="identity.disable_mfa",
                    rationale="Synthetic regression fixture adds one denied shortcut.",
                ),
            ),
        )
    )
    repository.append_run_event(
        RunEvent(
            event_id=f"{run_id}-fixture-approval",
            run_id=run_id,
            sequence=repository.next_event_sequence(run_id),
            occurred_at=occurred_at + timedelta(seconds=2),
            source=RunEventSource.OPERATOR,
            actor_type=ActorType.OPERATOR,
            correlation_id="fixture-approval",
            event_type=RunEventType.APPROVAL_RESOLVED,
            payload=ApprovalResolvedPayload(
                event_type=RunEventType.APPROVAL_RESOLVED,
                run_id=run_id,
                approval_request=ApprovalRequestRef(
                    approval_request_id="approval-fixture-regression-001",
                    run_id=run_id,
                    status=ApprovalRequestStatus.APPROVED,
                    requested_action_type="identity.reset_password",
                    tool_name="identity_api",
                    requester_role="agent",
                    requested_at=occurred_at + timedelta(seconds=1),
                    resolved_at=occurred_at + timedelta(seconds=2),
                    resolution_summary="Synthetic benchmark regression approval.",
                ).model_dump(mode="json"),
                operator_id="fixture-operator",
                decided_at=occurred_at + timedelta(seconds=2),
            ),
        )
    )
    repository.update_run_progress(
        run_id,
        status=RunStatus.FAILED,
        updated_at=occurred_at + timedelta(seconds=3),
        completed_at=occurred_at + timedelta(seconds=3),
        grade_result=GradeResult(
            grade_id="grade-fixture-regression-001",
            outcome=GradeOutcome.FAILED,
            score=0.25,
            summary="Synthetic regression fixture: candidate benchmark failed after an extra approval and denied shortcut.",
            rubric_version="v1",
        ),
    )


def _format_score(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.3f}"
