"""Atlas synth package exports."""

from atlas_core.package_info import PackageInfo

from atlas_synth.builder import (
    BASE_TIME,
    ENVIRONMENT_SLUG,
    FIXTURE_SLUG,
    build_canonical_world,
    summarize_world,
)
from atlas_synth.fixture import (
    CanonicalFixtureSession,
    clone_snapshot,
    render_snapshot_diff,
    snapshot_document,
)
from atlas_synth.models import (
    AccountAccessState,
    BaseWorldSnapshot,
    CompanyRecord,
    DepartmentRecord,
    DevicePlatform,
    DeviceRecord,
    DocCategory,
    EmployeeRecord,
    EmploymentStatus,
    HelpdeskTicketRecord,
    InboxMessageRecord,
    InboxThreadRecord,
    MessageChannel,
    ScenarioOverlayRecord,
    SuspiciousEventDisposition,
    SuspiciousEventRecord,
    SyntheticWorldSnapshot,
    SyntheticWorldSummary,
    TicketPriority,
    TicketStatus,
    WikiPageRecord,
)

PACKAGE_INFO = PackageInfo(
    name="atlas-synth",
    purpose="Synthetic company data and deterministic seeded fixture package.",
    phase_boundary="Phase 3 implements a canonical world builder without scenario overlays or generic world generation.",
)

__all__ = [
    "AccountAccessState",
    "BASE_TIME",
    "BaseWorldSnapshot",
    "CanonicalFixtureSession",
    "CompanyRecord",
    "DepartmentRecord",
    "DevicePlatform",
    "DeviceRecord",
    "DocCategory",
    "ENVIRONMENT_SLUG",
    "EmployeeRecord",
    "EmploymentStatus",
    "FIXTURE_SLUG",
    "HelpdeskTicketRecord",
    "InboxMessageRecord",
    "InboxThreadRecord",
    "MessageChannel",
    "PACKAGE_INFO",
    "ScenarioOverlayRecord",
    "SuspiciousEventDisposition",
    "SuspiciousEventRecord",
    "SyntheticWorldSnapshot",
    "SyntheticWorldSummary",
    "TicketPriority",
    "TicketStatus",
    "WikiPageRecord",
    "build_canonical_world",
    "clone_snapshot",
    "render_snapshot_diff",
    "snapshot_document",
    "summarize_world",
]
