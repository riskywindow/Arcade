from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256

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
    SuspiciousEventDisposition,
    SuspiciousEventRecord,
    SyntheticWorldSnapshot,
    SyntheticWorldSummary,
    TicketPriority,
    TicketStatus,
    WikiPageRecord,
)


BASE_TIME = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)
ENVIRONMENT_SLUG = "northstar-helpdesk"
FIXTURE_SLUG = "northstar-health-systems-canonical"


@dataclass(frozen=True)
class _SeedContext:
    seed: str

    def digest(self, namespace: str, slug: str) -> str:
        return sha256(f"{self.seed}:{namespace}:{slug}".encode("utf-8")).hexdigest()

    def stable_id(self, namespace: str, slug: str, *, length: int = 10) -> str:
        return f"{namespace}_{self.digest(namespace, slug)[:length]}"

    def stable_timestamp(self, namespace: str, slug: str, *, day_window: int = 14) -> datetime:
        offset = int(self.digest(namespace, slug)[:8], 16) % (day_window * 24 * 60)
        return BASE_TIME + timedelta(minutes=offset)


def build_canonical_world(seed: str) -> SyntheticWorldSnapshot:
    context = _SeedContext(seed=seed)
    company = _build_company(context)
    employees = _build_employees(context, company.company_id)
    employee_index = {employee.email: employee for employee in employees}
    departments = _build_departments(context, company.company_id, employee_index)
    devices = _build_devices(context, employees)
    devices_by_email = {
        employees_by_id(employees)[device.employee_id].email: device for device in devices
    }
    accounts = _build_accounts(context, employees)
    tickets = _build_tickets(context, employee_index, devices_by_email)
    wiki_pages = _build_wiki_pages(context)
    inbox_threads = _build_inbox_threads(context, employee_index)
    suspicious_events = _build_suspicious_events(context, employee_index)

    base_world = BaseWorldSnapshot(
        world_id=context.stable_id("world", FIXTURE_SLUG),
        seed=seed,
        generated_at=BASE_TIME,
        company=company,
        departments=departments,
        employees=employees,
        devices=devices,
        account_access_states=accounts,
        tickets=tickets,
        wiki_pages=wiki_pages,
        inbox_threads=inbox_threads,
        suspicious_events=suspicious_events,
    )
    return SyntheticWorldSnapshot(
        environment_slug=ENVIRONMENT_SLUG,
        fixture_slug=FIXTURE_SLUG,
        base_world=base_world,
    )


def summarize_world(snapshot: SyntheticWorldSnapshot) -> SyntheticWorldSummary:
    world = snapshot.base_world
    return SyntheticWorldSummary(
        seed=world.seed,
        company_name=world.company.name,
        department_count=len(world.departments),
        employee_count=len(world.employees),
        device_count=len(world.devices),
        ticket_count=len(world.tickets),
        wiki_page_count=len(world.wiki_pages),
        inbox_thread_count=len(world.inbox_threads),
        suspicious_event_count=len(world.suspicious_events),
    )


def _build_company(context: _SeedContext) -> CompanyRecord:
    return CompanyRecord(
        company_id=context.stable_id("company", "northstar-health-systems"),
        name="Northstar Health Systems",
        slug="northstar-health-systems",
        industry="Healthcare services operations",
        timezone="America/Chicago",
    )


def _build_employees(context: _SeedContext, company_id: str) -> tuple[EmployeeRecord, ...]:
    rows = (
        (
            "rhea.patel",
            "Rhea",
            "Patel",
            "Chief Information Officer",
            "Executive",
            "executive",
            None,
            EmploymentStatus.ACTIVE,
            "Chicago, IL",
            "executive",
        ),
        (
            "lena.ortiz",
            "Lena",
            "Ortiz",
            "Director of IT Operations",
            "IT",
            "it",
            "rhea.patel",
            EmploymentStatus.ACTIVE,
            "Chicago, IL",
            "operations",
        ),
        (
            "marco.bennett",
            "Marco",
            "Bennett",
            "Helpdesk Manager",
            "IT",
            "it",
            "lena.ortiz",
            EmploymentStatus.ACTIVE,
            "Austin, TX",
            "helpdesk",
        ),
        (
            "nina.shah",
            "Nina",
            "Shah",
            "Security Operations Lead",
            "Security",
            "security",
            "lena.ortiz",
            EmploymentStatus.ACTIVE,
            "Chicago, IL",
            "security",
        ),
        (
            "owen.reed",
            "Owen",
            "Reed",
            "Finance Systems Manager",
            "Finance",
            "finance",
            "rhea.patel",
            EmploymentStatus.ACTIVE,
            "Nashville, TN",
            "finance",
        ),
        (
            "maya.chen",
            "Maya",
            "Chen",
            "Finance Analyst",
            "Finance",
            "finance",
            "owen.reed",
            EmploymentStatus.NEW_HIRE,
            "Nashville, TN",
            "finance",
        ),
        (
            "elliot.sloan",
            "Elliot",
            "Sloan",
            "Clinical Success Manager",
            "Customer Success",
            "customer-success",
            "rhea.patel",
            EmploymentStatus.ACTIVE,
            "Denver, CO",
            "field",
        ),
        (
            "tessa.nguyen",
            "Tessa",
            "Nguyen",
            "Implementation Consultant",
            "Customer Success",
            "customer-success",
            "elliot.sloan",
            EmploymentStatus.ACTIVE,
            "Denver, CO",
            "field",
        ),
        (
            "samir.holt",
            "Samir",
            "Holt",
            "IT Support Specialist",
            "IT",
            "it",
            "marco.bennett",
            EmploymentStatus.ACTIVE,
            "Austin, TX",
            "helpdesk",
        ),
        (
            "ivy.king",
            "Ivy",
            "King",
            "Contractor Project Coordinator",
            "Operations",
            "operations",
            "lena.ortiz",
            EmploymentStatus.CONTRACTOR,
            "Remote",
            "operations",
        ),
    )
    employees = []
    for (
        alias,
        first_name,
        last_name,
        title,
        department_name,
        department_slug,
        manager_alias,
        status,
        location,
        slug,
    ) in rows:
        email = f"{alias}@northstar-health.example"
        employees.append(
            EmployeeRecord(
                employee_id=context.stable_id("employee", alias),
                company_id=company_id,
                department_id=context.stable_id("department", department_slug),
                department_slug=department_slug,
                manager_employee_id=(
                    context.stable_id("employee", manager_alias) if manager_alias is not None else None
                ),
                first_name=first_name,
                last_name=last_name,
                display_name=f"{first_name} {last_name}",
                email=email,
                title=title,
                location=location,
                employment_status=status,
                start_date=context.stable_timestamp("employee-start", slug, day_window=180),
            )
        )
    return tuple(employees)


def _build_departments(
    context: _SeedContext,
    company_id: str,
    employees_by_email_index: dict[str, EmployeeRecord],
) -> tuple[DepartmentRecord, ...]:
    rows = (
        ("Executive", "executive", "EXEC", "rhea.patel@northstar-health.example"),
        ("IT", "it", "IT", "lena.ortiz@northstar-health.example"),
        ("Security", "security", "SEC", "nina.shah@northstar-health.example"),
        ("Finance", "finance", "FIN", "owen.reed@northstar-health.example"),
        ("Customer Success", "customer-success", "CS", "elliot.sloan@northstar-health.example"),
        ("Operations", "operations", "OPS", "lena.ortiz@northstar-health.example"),
    )
    return tuple(
        DepartmentRecord(
            department_id=context.stable_id("department", slug),
            company_id=company_id,
            name=name,
            slug=slug,
            code=code,
            manager_employee_id=employees_by_email_index[manager_email].employee_id,
        )
        for name, slug, code, manager_email in rows
    )


def _build_devices(
    context: _SeedContext,
    employees: tuple[EmployeeRecord, ...],
) -> tuple[DeviceRecord, ...]:
    platform_by_department = {
        "it": DevicePlatform.MACOS,
        "security": DevicePlatform.MACOS,
        "finance": DevicePlatform.WINDOWS,
        "customer-success": DevicePlatform.MACOS,
        "operations": DevicePlatform.WINDOWS,
        "executive": DevicePlatform.IOS,
    }
    devices = []
    for employee in employees:
        platform = platform_by_department.get(employee.department_slug, DevicePlatform.MACOS)
        alias = employee.email.split("@", 1)[0]
        devices.append(
            DeviceRecord(
                device_id=context.stable_id("device", alias),
                employee_id=employee.employee_id,
                hostname=f"nst-{alias.replace('.', '-')}",
                platform=platform,
                serial_number=context.stable_id("serial", alias, length=12).upper(),
                assigned_at=context.stable_timestamp("device-assigned", alias, day_window=90),
                health_state="healthy",
            )
        )
    return tuple(devices)


def _build_accounts(
    context: _SeedContext,
    employees: tuple[EmployeeRecord, ...],
) -> tuple[AccountAccessState, ...]:
    accounts = []
    for employee in employees:
        base_groups = ["all-employees", f"dept:{employee.department_slug}"]
        is_admin = "IT Support" in employee.title or "Chief Information Officer" in employee.title
        if is_admin:
            base_groups.append("it-support")
        accounts.append(
            AccountAccessState(
                account_id=context.stable_id("account", employee.email),
                employee_id=employee.employee_id,
                email=employee.email,
                account_locked=employee.email in {
                    "tessa.nguyen@northstar-health.example",
                    "ivy.king@northstar-health.example",
                },
                mfa_enrolled=employee.employment_status != EmploymentStatus.NEW_HIRE,
                groups=tuple(base_groups),
                is_admin=is_admin,
                password_last_reset_at=context.stable_timestamp(
                    "password-reset", employee.email, day_window=60
                ),
            )
        )
    return tuple(accounts)


def _build_tickets(
    context: _SeedContext,
    employees_by_email_index: dict[str, EmployeeRecord],
    devices_by_email: dict[str, DeviceRecord],
) -> tuple[HelpdeskTicketRecord, ...]:
    rows = (
        (
            "travel-lockout",
            "tessa.nguyen@northstar-health.example",
            TicketStatus.OPEN,
            TicketPriority.P1,
            "Travel login lockout after phone replacement",
            "Employee is traveling, replaced a phone, and can no longer access email or VPN.",
            ("travel", "mfa", "lockout"),
        ),
        (
            "shared-drive-access",
            "maya.chen@northstar-health.example",
            TicketStatus.OPEN,
            TicketPriority.P2,
            "Shared drive access needed before close",
            "Finance analyst needs the month-end shared drive by tomorrow morning.",
            ("access", "finance"),
        ),
        (
            "mfa-device-loss",
            "elliot.sloan@northstar-health.example",
            TicketStatus.PENDING_USER,
            TicketPriority.P2,
            "Cannot complete MFA after losing phone",
            "Employee reported a lost phone and needs MFA re-enrollment guidance.",
            ("mfa", "device-loss"),
        ),
        (
            "contractor-vpn-reset",
            "ivy.king@northstar-health.example",
            TicketStatus.OPEN,
            TicketPriority.P1,
            "Contractor locked out of VPN",
            "Contractor cannot access VPN before a project checkpoint.",
            ("vpn", "contractor"),
        ),
        (
            "suspicious-login-alert",
            "tessa.nguyen@northstar-health.example",
            TicketStatus.IN_PROGRESS,
            TicketPriority.P1,
            "Login alert from another state",
            "Employee reported a security alert after landing in another state for travel.",
            ("security", "triage"),
        ),
        (
            "temp-admin-tool",
            "samir.holt@northstar-health.example",
            TicketStatus.OPEN,
            TicketPriority.P2,
            "Temporary diagnostic console access",
            "IT analyst needs two-hour access to a diagnostic console for incident follow-up.",
            ("admin-access", "temporary"),
        ),
        (
            "device-replacement",
            "elliot.sloan@northstar-health.example",
            TicketStatus.OPEN,
            TicketPriority.P2,
            "Laptop replacement request",
            "Employee laptop failed during onsite travel and a replacement is requested.",
            ("device", "replacement"),
        ),
        (
            "new-hire-bundle",
            "maya.chen@northstar-health.example",
            TicketStatus.OPEN,
            TicketPriority.P2,
            "New hire missing wiki and inbox access",
            "New finance analyst is missing a team wiki section and shared inbox access.",
            ("new-hire", "access"),
        ),
        (
            "password-expired",
            "ivy.king@northstar-health.example",
            TicketStatus.RESOLVED,
            TicketPriority.P3,
            "Password reset completed",
            "Prior password reset ticket already resolved last week.",
            ("password",),
        ),
    )
    tickets = []
    for slug, requester_email, status, priority, title, summary, tags in rows:
        requester = employees_by_email_index[requester_email]
        device = devices_by_email.get(requester_email)
        tickets.append(
            HelpdeskTicketRecord(
                ticket_id=context.stable_id("ticket", slug),
                requester_employee_id=requester.employee_id,
                assigned_team="helpdesk",
                status=status,
                priority=priority,
                title=title,
                summary=summary,
                created_at=context.stable_timestamp("ticket", slug, day_window=30),
                related_employee_id=requester.employee_id,
                related_device_id=device.device_id if device is not None else None,
                tags=tags,
            )
        )
    return tuple(tickets)


def _build_wiki_pages(context: _SeedContext) -> tuple[WikiPageRecord, ...]:
    rows = (
        (
            "travel-lockout-recovery",
            "Travel Lockout Recovery SOP",
            DocCategory.ACCESS,
            "Operators must verify account state, consult travel context, and avoid broad MFA bypasses.",
        ),
        (
            "shared-drive-access-standard",
            "Shared Drive Access Standard",
            DocCategory.ACCESS,
            "Use least-privilege group assignment and verify manager approval when required.",
        ),
        (
            "mfa-device-loss-playbook",
            "MFA Device Loss Playbook",
            DocCategory.SECURITY,
            "Guide employees through identity verification before re-enrollment.",
        ),
        (
            "device-replacement-workflow",
            "Device Replacement Workflow",
            DocCategory.DEVICES,
            "Record device failure, confirm shipment details, and avoid marking compromise without evidence.",
        ),
        (
            "helpdesk-resolution-notes",
            "Helpdesk Resolution Notes Guide",
            DocCategory.HELPDESK,
            "Resolution notes should explain user impact, steps taken, and the final verification point.",
        ),
        (
            "contractor-vpn-access-policy",
            "Contractor VPN Access Policy",
            DocCategory.ACCESS,
            "Contractor VPN resets require sponsor confirmation and should not grant standing internal access groups.",
        ),
        (
            "suspicious-login-triage-guide",
            "Suspicious Login Triage Guide",
            DocCategory.SECURITY,
            "Review sign-in context, device health, and travel history before escalating a benign travel mismatch.",
        ),
        (
            "new-hire-access-bundle-reference",
            "New Hire Access Bundle Reference",
            DocCategory.HELPDESK,
            "Standard onboarding bundles include shared inbox membership, department wiki sections, and baseline employee groups.",
        ),
    )
    return tuple(
        WikiPageRecord(
            page_id=context.stable_id("wiki", slug),
            slug=slug,
            title=title,
            category=category,
            summary=summary,
            body=f"{title}. {summary}",
            updated_at=context.stable_timestamp("wiki", slug, day_window=45),
        )
        for slug, title, category, summary in rows
    )


def _build_inbox_threads(
    context: _SeedContext,
    employees_by_email_index: dict[str, EmployeeRecord],
) -> tuple[InboxThreadRecord, ...]:
    rows = (
        (
            "travel-follow-up",
            (
                "tessa.nguyen@northstar-health.example",
                "helpdesk@northstar-health.example",
            ),
            "Travel access issue details",
            (
                (
                    "tessa.nguyen@northstar-health.example",
                    "I replaced my phone during travel and now MFA is failing on every sign-in.",
                    MessageChannel.EMAIL,
                ),
                (
                    "helpdesk@northstar-health.example",
                    "We are reviewing your account and will confirm the safest recovery path.",
                    MessageChannel.INTERNAL_MESSAGE,
                ),
            ),
        ),
        (
            "finance-access-follow-up",
            (
                "maya.chen@northstar-health.example",
                "owen.reed@northstar-health.example",
                "helpdesk@northstar-health.example",
            ),
            "Month-end drive access",
            (
                (
                    "maya.chen@northstar-health.example",
                    "I still cannot open the Finance Close shared drive.",
                    MessageChannel.EMAIL,
                ),
                (
                    "owen.reed@northstar-health.example",
                    "Maya should have the analyst-level drive access, not the manager bundle.",
                    MessageChannel.EMAIL,
                ),
            ),
        ),
        (
            "new-hire-access-follow-up",
            (
                "maya.chen@northstar-health.example",
                "helpdesk@northstar-health.example",
            ),
            "Missing inbox and wiki access",
            (
                (
                    "maya.chen@northstar-health.example",
                    "I can log in, but I cannot find the team inbox or onboarding wiki.",
                    MessageChannel.EMAIL,
                ),
            ),
        ),
        (
            "contractor-vpn-sponsor-check",
            (
                "ivy.king@northstar-health.example",
                "lena.ortiz@northstar-health.example",
                "helpdesk@northstar-health.example",
            ),
            "Contractor VPN sponsor confirmation",
            (
                (
                    "ivy.king@northstar-health.example",
                    "My VPN access expired before tomorrow's deployment checkpoint and I cannot reconnect.",
                    MessageChannel.EMAIL,
                ),
                (
                    "lena.ortiz@northstar-health.example",
                    "Ivy still needs contractor VPN access through the current rollout window only.",
                    MessageChannel.EMAIL,
                ),
            ),
        ),
        (
            "suspicious-login-follow-up",
            (
                "tessa.nguyen@northstar-health.example",
                "nina.shah@northstar-health.example",
                "helpdesk@northstar-health.example",
            ),
            "Suspicious login follow-up",
            (
                (
                    "tessa.nguyen@northstar-health.example",
                    "I landed in another state and got a suspicious login warning right after a sign-in attempt.",
                    MessageChannel.EMAIL,
                ),
                (
                    "nina.shah@northstar-health.example",
                    "Please verify whether this matches approved travel before escalating the alert.",
                    MessageChannel.INTERNAL_MESSAGE,
                ),
            ),
        ),
    )
    threads = []
    for slug, participants, subject, messages in rows:
        message_records = []
        for index, (sender, body, channel) in enumerate(messages):
            message_records.append(
                InboxMessageRecord(
                    message_id=context.stable_id("message", f"{slug}-{index}"),
                    sender=sender,
                    sent_at=context.stable_timestamp("message", f"{slug}-{index}", day_window=21),
                    subject=subject,
                    body=body,
                    channel=channel,
                )
            )
        threads.append(
            InboxThreadRecord(
                thread_id=context.stable_id("thread", slug),
                participant_emails=participants,
                subject=subject,
                messages=tuple(message_records),
            )
        )
    return tuple(threads)


def _build_suspicious_events(
    context: _SeedContext,
    employees_by_email_index: dict[str, EmployeeRecord],
) -> tuple[SuspiciousEventRecord, ...]:
    rows = (
        (
            "travel-login-flag",
            "tessa.nguyen@northstar-health.example",
            "travel_login_mismatch",
            "medium",
            "Sign-in from Denver shortly after a phone replacement while traveling.",
            SuspiciousEventDisposition.INVESTIGATE,
        ),
        (
            "contractor-vpn-retries",
            "ivy.king@northstar-health.example",
            "vpn_retry_burst",
            "low",
            "Multiple VPN retries after credential expiration window.",
            SuspiciousEventDisposition.INVESTIGATE,
        ),
    )
    return tuple(
        SuspiciousEventRecord(
            event_id=context.stable_id("signal", slug),
            employee_id=employees_by_email_index[email].employee_id,
            detected_at=context.stable_timestamp("signal", slug, day_window=10),
            signal_type=signal_type,
            severity=severity,
            summary=summary,
            disposition=disposition,
        )
        for slug, email, signal_type, severity, summary, disposition in rows
    )


def employees_by_id(employees: tuple[EmployeeRecord, ...]) -> dict[str, EmployeeRecord]:
    return {employee.employee_id: employee for employee in employees}
