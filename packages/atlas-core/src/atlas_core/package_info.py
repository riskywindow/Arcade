from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PackageInfo:
    name: str
    purpose: str
    phase_boundary: str


PACKAGE_INFO = PackageInfo(
    name="atlas-core",
    purpose="Shared Python foundation for runtime scaffolding and later domain contracts.",
    phase_boundary="No run, scenario, or task models are implemented in Phase 1.",
)
