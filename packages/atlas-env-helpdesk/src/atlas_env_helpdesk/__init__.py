"""Atlas helpdesk environment package shell."""

from atlas_core.package_info import PackageInfo

PACKAGE_INFO = PackageInfo(
    name="atlas-env-helpdesk",
    purpose="Helpdesk environment implementation boundary for the V1 domain.",
    phase_boundary="No environment logic, apps, or scenario behavior is implemented in Phase 1.",
)

__all__ = ["PACKAGE_INFO"]
