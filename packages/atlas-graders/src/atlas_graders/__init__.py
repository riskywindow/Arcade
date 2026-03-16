"""Atlas graders package shell."""

from atlas_core.package_info import PackageInfo

PACKAGE_INFO = PackageInfo(
    name="atlas-graders",
    purpose="Hidden grader and evaluation utility package boundary.",
    phase_boundary="No grader logic or rubric behavior is implemented in Phase 1.",
)

__all__ = ["PACKAGE_INFO"]
