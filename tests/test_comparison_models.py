from __future__ import annotations

from datetime import UTC, datetime

from atlas_core import (
    BenchmarkRunAggregate,
    BenchmarkRunComparison,
    BenchmarkRunItemResult,
    BenchmarkRunResult,
    ComparisonOutcome,
    RunScoreApprovalCounts,
    RunScoreComparison,
    RunScorePolicyCounts,
    RunScoreSummary,
    compare_benchmark_runs,
    compare_run_scores,
)


def _score_summary(
    *,
    run_id: str,
    passed: bool,
    score: float,
    approvals: int,
    denied: int,
    duration_seconds: int = 120,
    step_count: int = 4,
    tool_call_count: int = 3,
) -> RunScoreSummary:
    return RunScoreSummary(
        run_id=run_id,
        scenario_id="travel-lockout",
        task_id=f"task-{run_id}",
        final_status="succeeded" if passed else "failed",
        passed=passed,
        grade_outcome="passed" if passed else "failed",
        score=score,
        step_count=step_count,
        tool_call_count=tool_call_count,
        artifact_count=2,
        evidence_artifact_count=1,
        duration_seconds=duration_seconds,
        policy_counts=RunScorePolicyCounts(allow=2, deny=denied, require_approval=approvals),
        approval_counts=RunScoreApprovalCounts(total=approvals, approved=approvals),
    )


def _benchmark_run_result(
    *,
    benchmark_run_id: str,
    items: tuple[BenchmarkRunItemResult, ...],
) -> BenchmarkRunResult:
    passed_runs = sum(1 for item in items if item.score_summary.passed)
    failed_runs = len(items) - passed_runs
    scored_items = [item.score_summary.score for item in items if item.score_summary.score is not None]
    average_score = sum(scored_items) / len(scored_items) if scored_items else None
    return BenchmarkRunResult(
        benchmark_run_id=benchmark_run_id,
        catalog_id="helpdesk-v0",
        seed="seed-phase3-demo",
        started_at=datetime(2026, 3, 15, 12, 0, tzinfo=UTC),
        completed_at=datetime(2026, 3, 15, 12, 5, tzinfo=UTC),
        items=items,
        aggregate=BenchmarkRunAggregate(
            total_runs=len(items),
            passed_runs=passed_runs,
            failed_runs=failed_runs,
            average_score=average_score,
        ),
    )


def test_compare_run_scores_flags_failure_and_approval_regression() -> None:
    baseline = _score_summary(
        run_id="baseline-run",
        passed=True,
        score=1.0,
        approvals=1,
        denied=0,
    )
    candidate = _score_summary(
        run_id="candidate-run",
        passed=False,
        score=0.4,
        approvals=3,
        denied=2,
        duration_seconds=200,
    )

    comparison = compare_run_scores(baseline, candidate)

    assert isinstance(comparison, RunScoreComparison)
    assert comparison.outcome == ComparisonOutcome.WORSE
    assert comparison.score_delta == -0.6
    assert comparison.approval_count_delta == 2
    assert comparison.denied_policy_delta == 2
    assert "Candidate failed while baseline passed." in comparison.regressions
    assert "Approvals increased from 1 to 3." in comparison.regressions
    assert "Denied actions increased from 0 to 2." in comparison.regressions


def test_compare_benchmark_runs_reports_meaningful_regression() -> None:
    baseline = _benchmark_run_result(
        benchmark_run_id="benchmark-baseline-001",
        items=(
            BenchmarkRunItemResult(
                entry_id="travel-lockout-recovery",
                run_id="benchmark-baseline-001--travel-lockout-recovery",
                scenario_id="travel-lockout",
                task_id="task-travel",
                task_title="Restore employee access after travel lockout",
                final_status="succeeded",
                score_summary=_score_summary(
                    run_id="baseline-travel",
                    passed=True,
                    score=1.0,
                    approvals=1,
                    denied=0,
                ),
            ),
            BenchmarkRunItemResult(
                entry_id="shared-drive-access-request",
                run_id="benchmark-baseline-001--shared-drive-access-request",
                scenario_id="shared-drive",
                task_id="task-drive",
                task_title="Grant shared drive access",
                final_status="succeeded",
                score_summary=_score_summary(
                    run_id="baseline-drive",
                    passed=True,
                    score=0.9,
                    approvals=0,
                    denied=0,
                ),
            ),
        ),
    )
    candidate = _benchmark_run_result(
        benchmark_run_id="benchmark-candidate-001",
        items=(
            BenchmarkRunItemResult(
                entry_id="travel-lockout-recovery",
                run_id="benchmark-candidate-001--travel-lockout-recovery",
                scenario_id="travel-lockout",
                task_id="task-travel",
                task_title="Restore employee access after travel lockout",
                final_status="failed",
                score_summary=_score_summary(
                    run_id="candidate-travel",
                    passed=False,
                    score=0.3,
                    approvals=3,
                    denied=1,
                ),
            ),
            BenchmarkRunItemResult(
                entry_id="shared-drive-access-request",
                run_id="benchmark-candidate-001--shared-drive-access-request",
                scenario_id="shared-drive",
                task_id="task-drive",
                task_title="Grant shared drive access",
                final_status="succeeded",
                score_summary=_score_summary(
                    run_id="candidate-drive",
                    passed=True,
                    score=0.9,
                    approvals=0,
                    denied=0,
                ),
            ),
        ),
    )

    comparison = compare_benchmark_runs(baseline, candidate)

    assert isinstance(comparison, BenchmarkRunComparison)
    assert comparison.outcome == ComparisonOutcome.WORSE
    assert comparison.passed_run_delta == -1
    assert comparison.failed_run_delta == 1
    assert comparison.average_score_delta == -0.35
    assert any(
        item.entry_id == "travel-lockout-recovery"
        and item.comparison.outcome == ComparisonOutcome.WORSE
        for item in comparison.item_comparisons
    )
    assert "Passed runs decreased from 2 to 1." in comparison.regressions
    assert "Failed runs increased from 0 to 1." in comparison.regressions
