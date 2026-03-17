from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PackageInfo:
    name: str
    purpose: str
    phase_boundary: str


PACKAGE_INFO = PackageInfo(
    name="atlas-core",
    purpose="Shared Python domain models, lifecycle rules, serialization, and run persistence contracts.",
    phase_boundary="Environment logic, Bastion policies, hidden graders, and replay UI remain outside atlas-core through Phase 4.",
)
