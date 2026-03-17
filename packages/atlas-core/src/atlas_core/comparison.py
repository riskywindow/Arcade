from __future__ import annotations

from enum import StrEnum

from atlas_core.benchmark import BenchmarkRunResult
from atlas_core.domain import AtlasModel
from atlas_core.evaluation import RunScoreSummary


class ComparisonOutcome(StrEnum):
    BETTER = "better"
    WORSE = "worse"
    DIFFERENT = "different"
    SAME = "same"


class RunScoreComparison(AtlasModel):
    baseline: RunScoreSummary
    candidate: RunScoreSummary
    outcome: ComparisonOutcome
    summary: str
    regressions: tuple[str, ...] = ()
    improvements: tuple[str, ...] = ()
    score_delta: float | None = None
    step_count_delta: int = 0
    tool_call_count_delta: int = 0
    artifact_count_delta: int = 0
    duration_seconds_delta: int | None = None
    approval_count_delta: int = 0
    denied_policy_delta: int = 0


class BenchmarkEntryComparison(AtlasModel):
    entry_id: str
    task_title: str
    comparison: RunScoreComparison


class BenchmarkRunComparison(AtlasModel):
    baseline: BenchmarkRunResult
    candidate: BenchmarkRunResult
    outcome: ComparisonOutcome
    summary: str
    regressions: tuple[str, ...] = ()
    improvements: tuple[str, ...] = ()
    passed_run_delta: int = 0
    failed_run_delta: int = 0
    average_score_delta: float | None = None
    item_comparisons: tuple[BenchmarkEntryComparison, ...] = ()


def compare_run_scores(
    baseline: RunScoreSummary,
    candidate: RunScoreSummary,
) -> RunScoreComparison:
    regressions: list[str] = []
    improvements: list[str] = []

    score_delta = _float_delta(baseline.score, candidate.score)
    duration_delta = _int_delta(baseline.duration_seconds, candidate.duration_seconds)
    step_count_delta = candidate.step_count - baseline.step_count
    tool_call_count_delta = candidate.tool_call_count - baseline.tool_call_count
    artifact_count_delta = candidate.artifact_count - baseline.artifact_count
    approval_count_delta = candidate.approval_counts.total - baseline.approval_counts.total
    denied_policy_delta = candidate.policy_counts.deny - baseline.policy_counts.deny

    if baseline.passed and not candidate.passed:
        regressions.append("Candidate failed while baseline passed.")
    elif candidate.passed and not baseline.passed:
        improvements.append("Candidate passed while baseline failed.")

    if score_delta is not None:
        if score_delta < 0:
            regressions.append(
                f"Score dropped from {baseline.score:.2f} to {candidate.score:.2f}."
            )
        elif score_delta > 0:
            improvements.append(
                f"Score improved from {baseline.score:.2f} to {candidate.score:.2f}."
            )

    if denied_policy_delta > 0:
        regressions.append(
            f"Denied actions increased from {baseline.policy_counts.deny} to {candidate.policy_counts.deny}."
        )
    elif denied_policy_delta < 0:
        improvements.append(
            f"Denied actions decreased from {baseline.policy_counts.deny} to {candidate.policy_counts.deny}."
        )

    if approval_count_delta > 0:
        regressions.append(
            f"Approvals increased from {baseline.approval_counts.total} to {candidate.approval_counts.total}."
        )
    elif approval_count_delta < 0:
        improvements.append(
            f"Approvals decreased from {baseline.approval_counts.total} to {candidate.approval_counts.total}."
        )

    outcome = _comparison_outcome(
        regressions=tuple(regressions),
        improvements=tuple(improvements),
        changed=_tracked_fields_changed(
            baseline,
            candidate,
            score_delta=score_delta,
            duration_delta=duration_delta,
            step_count_delta=step_count_delta,
            tool_call_count_delta=tool_call_count_delta,
            artifact_count_delta=artifact_count_delta,
            approval_count_delta=approval_count_delta,
            denied_policy_delta=denied_policy_delta,
        ),
    )
    return RunScoreComparison(
        baseline=baseline,
        candidate=candidate,
        outcome=outcome,
        summary=_run_comparison_summary(outcome, regressions, improvements),
        regressions=tuple(regressions),
        improvements=tuple(improvements),
        score_delta=score_delta,
        step_count_delta=step_count_delta,
        tool_call_count_delta=tool_call_count_delta,
        artifact_count_delta=artifact_count_delta,
        duration_seconds_delta=duration_delta,
        approval_count_delta=approval_count_delta,
        denied_policy_delta=denied_policy_delta,
    )


def compare_benchmark_runs(
    baseline: BenchmarkRunResult,
    candidate: BenchmarkRunResult,
) -> BenchmarkRunComparison:
    regressions: list[str] = []
    improvements: list[str] = []
    baseline_items = {item.entry_id: item for item in baseline.items}
    candidate_items = {item.entry_id: item for item in candidate.items}

    missing_entries = sorted(set(baseline_items) - set(candidate_items))
    extra_entries = sorted(set(candidate_items) - set(baseline_items))
    for entry_id in missing_entries:
        regressions.append(f"Candidate is missing benchmark entry {entry_id}.")
    for entry_id in extra_entries:
        improvements.append(f"Candidate added benchmark entry {entry_id}.")

    item_comparisons: list[BenchmarkEntryComparison] = []
    for entry_id in sorted(set(baseline_items).intersection(candidate_items)):
        baseline_item = baseline_items[entry_id]
        candidate_item = candidate_items[entry_id]
        item_comparison = compare_run_scores(
            baseline_item.score_summary,
            candidate_item.score_summary,
        )
        if item_comparison.outcome == ComparisonOutcome.WORSE:
            regressions.append(
                f"{entry_id} regressed: {item_comparison.summary}"
            )
        elif item_comparison.outcome == ComparisonOutcome.BETTER:
            improvements.append(
                f"{entry_id} improved: {item_comparison.summary}"
            )
        item_comparisons.append(
            BenchmarkEntryComparison(
                entry_id=entry_id,
                task_title=candidate_item.task_title,
                comparison=item_comparison,
            )
        )

    passed_run_delta = candidate.aggregate.passed_runs - baseline.aggregate.passed_runs
    failed_run_delta = candidate.aggregate.failed_runs - baseline.aggregate.failed_runs
    average_score_delta = _float_delta(
        baseline.aggregate.average_score,
        candidate.aggregate.average_score,
    )

    if passed_run_delta < 0:
        regressions.append(
            f"Passed runs decreased from {baseline.aggregate.passed_runs} to {candidate.aggregate.passed_runs}."
        )
    elif passed_run_delta > 0:
        improvements.append(
            f"Passed runs increased from {baseline.aggregate.passed_runs} to {candidate.aggregate.passed_runs}."
        )

    if failed_run_delta > 0:
        regressions.append(
            f"Failed runs increased from {baseline.aggregate.failed_runs} to {candidate.aggregate.failed_runs}."
        )
    elif failed_run_delta < 0:
        improvements.append(
            f"Failed runs decreased from {baseline.aggregate.failed_runs} to {candidate.aggregate.failed_runs}."
        )

    if average_score_delta is not None:
        if average_score_delta < 0:
            regressions.append(
                f"Average score dropped from {baseline.aggregate.average_score:.2f} to {candidate.aggregate.average_score:.2f}."
            )
        elif average_score_delta > 0:
            improvements.append(
                f"Average score improved from {baseline.aggregate.average_score:.2f} to {candidate.aggregate.average_score:.2f}."
            )

    outcome = _comparison_outcome(
        regressions=tuple(regressions),
        improvements=tuple(improvements),
        changed=(
            bool(missing_entries)
            or bool(extra_entries)
            or passed_run_delta != 0
            or failed_run_delta != 0
            or average_score_delta not in (None, 0.0)
            or any(item.comparison.outcome != ComparisonOutcome.SAME for item in item_comparisons)
        ),
    )
    return BenchmarkRunComparison(
        baseline=baseline,
        candidate=candidate,
        outcome=outcome,
        summary=_benchmark_comparison_summary(outcome, regressions, improvements),
        regressions=tuple(regressions),
        improvements=tuple(improvements),
        passed_run_delta=passed_run_delta,
        failed_run_delta=failed_run_delta,
        average_score_delta=average_score_delta,
        item_comparisons=tuple(item_comparisons),
    )


def _tracked_fields_changed(
    baseline: RunScoreSummary,
    candidate: RunScoreSummary,
    *,
    score_delta: float | None,
    duration_delta: int | None,
    step_count_delta: int,
    tool_call_count_delta: int,
    artifact_count_delta: int,
    approval_count_delta: int,
    denied_policy_delta: int,
) -> bool:
    return any(
        (
            baseline.passed != candidate.passed,
            baseline.grade_outcome != candidate.grade_outcome,
            score_delta not in (None, 0.0),
            duration_delta not in (None, 0),
            step_count_delta != 0,
            tool_call_count_delta != 0,
            artifact_count_delta != 0,
            approval_count_delta != 0,
            denied_policy_delta != 0,
        )
    )


def _comparison_outcome(
    *,
    regressions: tuple[str, ...],
    improvements: tuple[str, ...],
    changed: bool,
) -> ComparisonOutcome:
    if regressions and not improvements:
        return ComparisonOutcome.WORSE
    if improvements and not regressions:
        return ComparisonOutcome.BETTER
    if not changed:
        return ComparisonOutcome.SAME
    return ComparisonOutcome.DIFFERENT


def _run_comparison_summary(
    outcome: ComparisonOutcome,
    regressions: list[str],
    improvements: list[str],
) -> str:
    if outcome == ComparisonOutcome.WORSE:
        return regressions[0]
    if outcome == ComparisonOutcome.BETTER:
        return improvements[0]
    if outcome == ComparisonOutcome.SAME:
        return "Candidate matches the baseline on the tracked score fields."
    if regressions and improvements:
        return f"{improvements[0]} {regressions[0]}"
    return "Candidate differs from the baseline on the tracked score fields."


def _benchmark_comparison_summary(
    outcome: ComparisonOutcome,
    regressions: list[str],
    improvements: list[str],
) -> str:
    if outcome == ComparisonOutcome.WORSE:
        return regressions[0]
    if outcome == ComparisonOutcome.BETTER:
        return improvements[0]
    if outcome == ComparisonOutcome.SAME:
        return "Candidate benchmark matches the baseline on the tracked benchmark fields."
    if regressions and improvements:
        return f"{improvements[0]} {regressions[0]}"
    return "Candidate benchmark differs from the baseline on the tracked benchmark fields."


def _float_delta(baseline: float | None, candidate: float | None) -> float | None:
    if baseline is None or candidate is None:
        return None
    return round(candidate - baseline, 4)


def _int_delta(baseline: int | None, candidate: int | None) -> int | None:
    if baseline is None or candidate is None:
        return None
    return candidate - baseline
