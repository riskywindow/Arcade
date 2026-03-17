from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SynthModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DevicePlatform(StrEnum):
    MACOS = "macos"
    WINDOWS = "windows"
    IOS = "ios"


class EmploymentStatus(StrEnum):
    ACTIVE = "active"
    CONTRACTOR = "contractor"
    NEW_HIRE = "new_hire"
    TERMINATING = "terminating"


class TicketStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING_USER = "pending_user"
    RESOLVED = "resolved"


class TicketPriority(StrEnum):
    P1 = "p1"
    P2 = "p2"
    P3 = "p3"


class DocCategory(StrEnum):
    ACCESS = "access"
    SECURITY = "security"
    DEVICES = "devices"
    HELPDESK = "helpdesk"


class MessageChannel(StrEnum):
    EMAIL = "email"
    INTERNAL_MESSAGE = "internal_message"


class SuspiciousEventDisposition(StrEnum):
    BENIGN = "benign"
    INVESTIGATE = "investigate"
    ESCALATE = "escalate"


class CompanyRecord(SynthModel):
    company_id: str
    name: str
    slug: str
    industry: str
    timezone: str


class DepartmentRecord(SynthModel):
    department_id: str
    company_id: str
    name: str
    slug: str
    code: str
    manager_employee_id: str


class EmployeeRecord(SynthModel):
    employee_id: str
    company_id: str
    department_id: str
    department_slug: str
    manager_employee_id: str | None = None
    first_name: str
    last_name: str
    display_name: str
    email: str
    title: str
    location: str
    employment_status: EmploymentStatus
    start_date: datetime


class DeviceRecord(SynthModel):
    device_id: str
    employee_id: str
    hostname: str
    platform: DevicePlatform
    serial_number: str
    assigned_at: datetime
    health_state: str
    compromised: bool = False


class AccountAccessState(SynthModel):
    account_id: str
    employee_id: str
    email: str
    account_locked: bool
    mfa_enrolled: bool
    groups: tuple[str, ...]
    is_admin: bool = False
    password_last_reset_at: datetime


class HelpdeskTicketRecord(SynthModel):
    ticket_id: str
    requester_employee_id: str
    assigned_team: str
    status: TicketStatus
    priority: TicketPriority
    title: str
    summary: str
    created_at: datetime
    related_employee_id: str | None = None
    related_device_id: str | None = None
    tags: tuple[str, ...] = ()


class WikiPageRecord(SynthModel):
    page_id: str
    slug: str
    title: str
    category: DocCategory
    summary: str
    body: str
    updated_at: datetime


class InboxMessageRecord(SynthModel):
    message_id: str
    sender: str
    sent_at: datetime
    subject: str
    body: str
    channel: MessageChannel


class InboxThreadRecord(SynthModel):
    thread_id: str
    participant_emails: tuple[str, ...]
    subject: str
    messages: tuple[InboxMessageRecord, ...]


class SuspiciousEventRecord(SynthModel):
    event_id: str
    employee_id: str
    detected_at: datetime
    signal_type: str
    severity: str
    summary: str
    disposition: SuspiciousEventDisposition


class BaseWorldSnapshot(SynthModel):
    world_id: str
    seed: str
    generated_at: datetime
    company: CompanyRecord
    departments: tuple[DepartmentRecord, ...]
    employees: tuple[EmployeeRecord, ...]
    devices: tuple[DeviceRecord, ...]
    account_access_states: tuple[AccountAccessState, ...]
    tickets: tuple[HelpdeskTicketRecord, ...]
    wiki_pages: tuple[WikiPageRecord, ...]
    inbox_threads: tuple[InboxThreadRecord, ...]
    suspicious_events: tuple[SuspiciousEventRecord, ...]


class ScenarioOverlayRecord(SynthModel):
    overlay_id: str
    overlay_kind: str
    summary: str
    target_ids: tuple[str, ...] = ()


class SyntheticWorldSnapshot(SynthModel):
    schema_version: int = Field(default=1, ge=1)
    environment_slug: str
    fixture_slug: str
    base_world: BaseWorldSnapshot
    scenario_overlays: tuple[ScenarioOverlayRecord, ...] = ()


class SyntheticWorldSummary(SynthModel):
    seed: str
    company_name: str
    department_count: int
    employee_count: int
    device_count: int
    ticket_count: int
    wiki_page_count: int
    inbox_thread_count: int
    suspicious_event_count: int
