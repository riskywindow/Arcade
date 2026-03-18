from __future__ import annotations

import ast
from collections.abc import Generator
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
import uuid

import psycopg
import pytest
from psycopg.rows import dict_row

from atlas_core import (
    BenchmarkRunAggregate,
    BenchmarkRunItemResult,
    BenchmarkRunResult,
    DEFAULT_MIGRATIONS_DIR,
    RunRepository,
    RunScoreApprovalCounts,
    RunScorePolicyCounts,
    RunScoreSummary,
    RunService,
    apply_migrations,
    compare_benchmark_runs,
    discover_migrations,
)
from atlas_core.comparison import ComparisonOutcome
from atlas_core.config import InfrastructureConfig
from atlas_worker.benchmark_fixture import (
    DEFAULT_BASELINE_BENCHMARK_RUN_ID,
    DEFAULT_CANDIDATE_BENCHMARK_RUN_ID,
    execute_benchmark_fixture,
    render_benchmark_sample_report,
)
from atlas_worker.main import main


def _connect() -> psycopg.Connection[dict[str, object]] | None:
    dsn = InfrastructureConfig.from_env().postgres_dsn()
    try:
        return psycopg.connect(dsn, autocommit=True, row_factory=dict_row)
    except psycopg.OperationalError:
        return None


def _score_summary(run_id: str, *, passed: bool, score: float, approvals: int, denies: int) -> RunScoreSummary:
    return RunScoreSummary(
        run_id=run_id,
        scenario_id=run_id,
        task_id=f"task-{run_id}",
        final_status="succeeded" if passed else "failed",
        passed=passed,
        grade_outcome="passed" if passed else "failed",
        score=score,
        step_count=3,
        tool_call_count=2,
        artifact_count=1,
        evidence_artifact_count=1,
        duration_seconds=120,
        policy_counts=RunScorePolicyCounts(allow=2, deny=denies, require_approval=approvals),
        approval_counts=RunScoreApprovalCounts(total=approvals, approved=approvals),
    )


def _benchmark_result(
    benchmark_run_id: str,
    items: tuple[BenchmarkRunItemResult, ...],
) -> BenchmarkRunResult:
    scored_items = [item.score_summary.score for item in items if item.score_summary.score is not None]
    passed_runs = sum(1 for item in items if item.score_summary.passed)
    return BenchmarkRunResult(
        benchmark_run_id=benchmark_run_id,
        catalog_id="helpdesk-v0",
        seed="seed-phase3-demo",
        started_at=datetime(2026, 3, 17, 12, 0, tzinfo=UTC),
        completed_at=datetime(2026, 3, 17, 12, 5, tzinfo=UTC),
        items=items,
        aggregate=BenchmarkRunAggregate(
            total_runs=len(items),
            passed_runs=passed_runs,
            failed_runs=len(items) - passed_runs,
            average_score=sum(scored_items) / len(scored_items),
        ),
    )


@pytest.fixture
def isolated_worker_service() -> Generator[tuple[RunService, str], None, None]:
    conn = _connect()
    if conn is None:
        pytest.skip("local Postgres is not available")

    schema_name = f"test_worker_benchmark_fixture_{uuid.uuid4().hex[:8]}"
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


def test_execute_benchmark_fixture_creates_regressed_candidate_and_report(
    isolated_worker_service: tuple[RunService, str],
    tmp_path,
) -> None:
    service, _ = isolated_worker_service
    report_path = tmp_path / "phase6-sample-report.md"

    fixture = execute_benchmark_fixture(
        service,
        sample_report_path=report_path,
    )

    assert fixture.catalog_id == "helpdesk-v0"
    assert fixture.baseline.benchmark_run_id == DEFAULT_BASELINE_BENCHMARK_RUN_ID
    assert fixture.candidate.benchmark_run_id == DEFAULT_CANDIDATE_BENCHMARK_RUN_ID
    assert fixture.comparison.outcome == ComparisonOutcome.WORSE
    assert fixture.candidate.aggregate.passed_runs == 1
    assert fixture.candidate.aggregate.failed_runs == 1
    assert fixture.candidate.aggregate.average_score == 0.625
    assert fixture.comparison.passed_run_delta == -1
    assert fixture.comparison.failed_run_delta == 1
    assert any(
        "Denied actions increased" in regression
        for regression in fixture.comparison.regressions
    )
    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    assert "# Phase 6 Sample Benchmark Report" in report_text
    assert "- Candidate benchmark: `benchmark-helpdesk-v0-regressed`" in report_text
    assert "- Passed runs: `1/2`" in report_text
    assert "| Restore employee access after travel lockout | failed | 0.250 | 1 | 1 | Candidate failed while baseline passed. |" in report_text


def test_render_benchmark_sample_report_uses_comparison_numbers() -> None:
    baseline = _benchmark_result(
        "benchmark-helpdesk-v0-baseline",
        (
            BenchmarkRunItemResult(
                entry_id="travel-lockout-recovery",
                run_id="baseline--travel",
                scenario_id="travel-lockout-recovery",
                task_id="task-travel",
                task_title="Restore employee access after travel lockout",
                final_status="succeeded",
                score_summary=_score_summary(
                    "baseline-travel",
                    passed=True,
                    score=1.0,
                    approvals=0,
                    denies=0,
                ),
            ),
            BenchmarkRunItemResult(
                entry_id="shared-drive-access-request",
                run_id="baseline--drive",
                scenario_id="shared-drive-access-request",
                task_id="task-drive",
                task_title="Grant the correct finance shared drive access",
                final_status="succeeded",
                score_summary=_score_summary(
                    "baseline-drive",
                    passed=True,
                    score=1.0,
                    approvals=0,
                    denies=0,
                ),
            ),
        ),
    )
    candidate = _benchmark_result(
        "benchmark-helpdesk-v0-regressed",
        (
            BenchmarkRunItemResult(
                entry_id="travel-lockout-recovery",
                run_id="candidate--travel",
                scenario_id="travel-lockout-recovery",
                task_id="task-travel",
                task_title="Restore employee access after travel lockout",
                final_status="failed",
                score_summary=_score_summary(
                    "candidate-travel",
                    passed=False,
                    score=0.25,
                    approvals=1,
                    denies=1,
                ),
            ),
            BenchmarkRunItemResult(
                entry_id="shared-drive-access-request",
                run_id="candidate--drive",
                scenario_id="shared-drive-access-request",
                task_id="task-drive",
                task_title="Grant the correct finance shared drive access",
                final_status="succeeded",
                score_summary=_score_summary(
                    "candidate-drive",
                    passed=True,
                    score=1.0,
                    approvals=0,
                    denies=0,
                ),
            ),
        ),
    )
    comparison = compare_benchmark_runs(baseline, candidate)

    report = render_benchmark_sample_report(
        baseline=baseline,
        candidate=candidate,
        comparison=comparison,
    )

    assert "- Passed runs: `1/2`" in report
    assert "- Average score: `0.625`" in report
    assert "- Approval count: `1`" in report
    assert "- Denied policy count: `1`" in report
    assert "travel-lockout-recovery regressed: Candidate failed while baseline passed." in report
    assert "| Restore employee access after travel lockout | failed | 0.250 | 1 | 1 | Candidate failed while baseline passed. |" in report
    assert "| Grant the correct finance shared drive access | passed | 1.000 | 0 | 0 | Candidate matches the baseline on the tracked score fields. |" in report


def test_checked_in_sample_report_matches_rendered_fixture_template() -> None:
    baseline = _benchmark_result(
        "benchmark-helpdesk-v0-baseline",
        (
            BenchmarkRunItemResult(
                entry_id="travel-lockout-recovery",
                run_id="baseline--travel",
                scenario_id="travel-lockout-recovery",
                task_id="task_travel_lockout_recovery",
                task_title="Restore employee access after travel lockout",
                final_status="succeeded",
                score_summary=_score_summary(
                    "baseline-travel",
                    passed=True,
                    score=1.0,
                    approvals=0,
                    denies=0,
                ),
            ),
            BenchmarkRunItemResult(
                entry_id="shared-drive-access-request",
                run_id="baseline--drive",
                scenario_id="shared-drive-access-request",
                task_id="task_shared_drive_access_request",
                task_title="Grant the correct finance shared drive access",
                final_status="succeeded",
                score_summary=_score_summary(
                    "baseline-drive",
                    passed=True,
                    score=1.0,
                    approvals=0,
                    denies=0,
                ),
            ),
        ),
    )
    candidate = _benchmark_result(
        "benchmark-helpdesk-v0-regressed",
        (
            BenchmarkRunItemResult(
                entry_id="travel-lockout-recovery",
                run_id="candidate--travel",
                scenario_id="travel-lockout-recovery",
                task_id="task_travel_lockout_recovery",
                task_title="Restore employee access after travel lockout",
                final_status="failed",
                score_summary=_score_summary(
                    "candidate-travel",
                    passed=False,
                    score=0.25,
                    approvals=1,
                    denies=1,
                ),
            ),
            BenchmarkRunItemResult(
                entry_id="shared-drive-access-request",
                run_id="candidate--drive",
                scenario_id="shared-drive-access-request",
                task_id="task_shared_drive_access_request",
                task_title="Grant the correct finance shared drive access",
                final_status="succeeded",
                score_summary=_score_summary(
                    "candidate-drive",
                    passed=True,
                    score=1.0,
                    approvals=0,
                    denies=0,
                ),
            ),
        ),
    )
    comparison = compare_benchmark_runs(baseline, candidate)
    rendered = render_benchmark_sample_report(
        baseline=baseline,
        candidate=candidate,
        comparison=comparison,
    )

    checked_in_report = Path("docs/demos/phase6-benchmark-sample-report.md").read_text(
        encoding="utf-8",
    )

    assert checked_in_report == rendered


def test_worker_main_benchmark_fixture_command(
    isolated_worker_service: tuple[RunService, str],
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, schema_name = isolated_worker_service
    report_path = tmp_path / "phase6-cli-report.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "atlas-worker",
            "benchmark-fixture",
            "--schema-name",
            schema_name,
            "--catalog-id",
            "helpdesk-v0",
            "--baseline-benchmark-run-id",
            "benchmark-cli-baseline",
            "--candidate-benchmark-run-id",
            "benchmark-cli-regressed",
            "--sample-report-path",
            str(report_path),
        ],
    )

    main()

    output = ast.literal_eval(capsys.readouterr().out.strip())
    assert output["catalog_id"] == "helpdesk-v0"
    assert output["baseline_benchmark_run_id"] == "benchmark-cli-baseline"
    assert output["candidate_benchmark_run_id"] == "benchmark-cli-regressed"
    assert output["comparison_outcome"] == "worse"
    assert output["passed_runs"] == 1
    assert output["failed_runs"] == 1
    assert output["average_score"] == 0.625
    assert output["sample_report_path"] == str(report_path)
    assert report_path.exists()
