"""Model gateway package shell."""

from atlas_core.package_info import PackageInfo

PACKAGE_INFO = PackageInfo(
    name="model-gateway",
    purpose="Model/provider abstraction boundary for later runtime integration.",
    phase_boundary="No provider integration or request logic is implemented in Phase 1.",
)

__all__ = ["PACKAGE_INFO"]
