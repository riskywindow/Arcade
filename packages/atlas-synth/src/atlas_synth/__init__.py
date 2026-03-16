"""Atlas synth package shell."""

from atlas_core.package_info import PackageInfo

PACKAGE_INFO = PackageInfo(
    name="atlas-synth",
    purpose="Synthetic company data and seeded fixture package boundary.",
    phase_boundary="No seeded company generation or fixture logic is implemented in Phase 1.",
)

__all__ = ["PACKAGE_INFO"]
