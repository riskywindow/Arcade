"""Atlas graders exports."""

from atlas_core.package_info import PackageInfo

from atlas_graders.helpdesk import HelpdeskObservedEvidence, grade_helpdesk_scenario

PACKAGE_INFO = PackageInfo(
    name="atlas-graders",
    purpose="Hidden grader implementations and deterministic evaluation helpers.",
    phase_boundary="Phase 3 adds deterministic helpdesk graders without a benchmark runner or LLM judge.",
)

__all__ = [
    "HelpdeskObservedEvidence",
    "PACKAGE_INFO",
    "grade_helpdesk_scenario",
]
