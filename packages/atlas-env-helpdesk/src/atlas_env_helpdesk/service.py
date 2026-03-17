from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from atlas_synth import BASE_TIME, CanonicalFixtureSession, TicketStatus


class HelpdeskServiceError(Exception):
    """Base error for helpdesk service operations."""


class HelpdeskTicketNotFoundError(HelpdeskServiceError):
    """Raised when a ticket does not exist."""


class EmployeeNotFoundError(HelpdeskServiceError):
    """Raised when an employee does not exist."""


class InvalidTicketTransitionError(HelpdeskServiceError):
    """Raised when a ticket status transition is not allowed."""


class WikiDocumentNotFoundError(HelpdeskServiceError):
    """Raised when a wiki document does not exist."""


class InboxThreadNotFoundError(HelpdeskServiceError):
    """Raised when an inbox thread does not exist."""


class AccountAccessNotFoundError(HelpdeskServiceError):
    """Raised when an account access record does not exist."""


class DeviceNotFoundError(HelpdeskServiceError):
    """Raised when a device record does not exist."""


class SuspiciousEventNotFoundError(HelpdeskServiceError):
    """Raised when a suspicious event record does not exist."""


class HelpdeskStateModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class NoteKind(StrEnum):
    INTERNAL = "internal"
    CUSTOMER = "customer"
    RESOLUTION = "resolution"


class TicketNote(HelpdeskStateModel):
    note_id: str
    ticket_id: str
    author: str
    body: str
    kind: NoteKind
    created_at: datetime


class EmployeeSummary(HelpdeskStateModel):
    employee_id: str
    display_name: str
    email: str
    title: str
    department_slug: str
    manager_employee_id: str | None = None


class DeviceSummary(HelpdeskStateModel):
    device_id: str
    employee_id: str
    hostname: str
    platform: str
    health_state: str
    compromised: bool
    assigned_at: datetime
    serial_number: str


class AccountAccessSummary(HelpdeskStateModel):
    account_id: str
    email: str
    account_locked: bool
    mfa_enrolled: bool
    groups: tuple[str, ...]
    is_admin: bool
    password_last_reset_at: datetime


class SuspiciousEventSummary(HelpdeskStateModel):
    event_id: str
    employee_id: str
    detected_at: datetime
    signal_type: str
    severity: str
    summary: str
    disposition: str


class HelpdeskTicketRecord(HelpdeskStateModel):
    ticket_id: str
    requester_employee_id: str
    assigned_team: str
    assigned_to: str | None = None
    status: TicketStatus
    priority: str
    title: str
    summary: str
    created_at: datetime
    updated_at: datetime
    related_employee_id: str | None = None
    related_device_id: str | None = None
    tags: tuple[str, ...] = ()
    notes: tuple[TicketNote, ...] = ()


class HelpdeskTicketDetail(HelpdeskStateModel):
    ticket: HelpdeskTicketRecord
    requester: EmployeeSummary
    related_employee: EmployeeSummary | None = None
    related_device: DeviceSummary | None = None


class TicketQueue(HelpdeskStateModel):
    seed: str
    tickets: tuple[HelpdeskTicketRecord, ...]


class DirectoryEmployeeRecord(HelpdeskStateModel):
    employee_id: str
    display_name: str
    email: str
    title: str
    department_slug: str
    employment_status: str
    location: str
    manager_employee_id: str | None = None
    start_date: datetime


class EmployeeDirectory(HelpdeskStateModel):
    seed: str
    employees: tuple[DirectoryEmployeeRecord, ...]


class EmployeeDirectoryDetail(HelpdeskStateModel):
    employee: DirectoryEmployeeRecord
    manager: EmployeeSummary | None = None
    devices: tuple[DeviceSummary, ...]
    account_access: AccountAccessSummary
    related_tickets: tuple[HelpdeskTicketRecord, ...]
    suspicious_events: tuple[SuspiciousEventSummary, ...]


class WikiDocumentRecord(HelpdeskStateModel):
    page_id: str
    slug: str
    title: str
    category: str
    summary: str
    body: str
    updated_at: datetime


class WikiDocumentList(HelpdeskStateModel):
    seed: str
    documents: tuple[WikiDocumentRecord, ...]


class WikiSearchResult(HelpdeskStateModel):
    document: WikiDocumentRecord
    score: int
    matched_terms: tuple[str, ...]


class WikiSearchResponse(HelpdeskStateModel):
    seed: str
    query: str
    results: tuple[WikiSearchResult, ...]


class InboxMessageRecord(HelpdeskStateModel):
    message_id: str
    sender: str
    sent_at: datetime
    subject: str
    body: str
    channel: str


class InboxThreadRecord(HelpdeskStateModel):
    thread_id: str
    participant_emails: tuple[str, ...]
    subject: str
    messages: tuple[InboxMessageRecord, ...]
    last_message_at: datetime
    message_count: int


class InboxThreadList(HelpdeskStateModel):
    seed: str
    threads: tuple[InboxThreadRecord, ...]


ALLOWED_STATUS_TRANSITIONS: dict[TicketStatus, frozenset[TicketStatus]] = {
    TicketStatus.OPEN: frozenset(
        {
            TicketStatus.IN_PROGRESS,
            TicketStatus.PENDING_USER,
            TicketStatus.RESOLVED,
        }
    ),
    TicketStatus.IN_PROGRESS: frozenset(
        {
            TicketStatus.OPEN,
            TicketStatus.PENDING_USER,
            TicketStatus.RESOLVED,
        }
    ),
    TicketStatus.PENDING_USER: frozenset(
        {
            TicketStatus.OPEN,
            TicketStatus.IN_PROGRESS,
            TicketStatus.RESOLVED,
        }
    ),
    TicketStatus.RESOLVED: frozenset(
        {
            TicketStatus.OPEN,
            TicketStatus.IN_PROGRESS,
        }
    ),
}


class HelpdeskService:
    def __init__(self, *, seed: str) -> None:
        self._seed = seed
        self._fixture = CanonicalFixtureSession.load(seed)
        self._mutation_counter = 0
        self._reset_runtime_state()

    @classmethod
    def seeded(cls, seed: str = "seed-phase3-demo") -> "HelpdeskService":
        return cls(seed=seed)

    @property
    def seed(self) -> str:
        return self._seed

    def list_ticket_queue(self) -> TicketQueue:
        return TicketQueue(
            seed=self._seed,
            tickets=tuple(
                self._ticket_records[ticket_id] for ticket_id in sorted(self._ticket_records.keys())
            ),
        )

    def get_ticket_detail(self, ticket_id: str) -> HelpdeskTicketDetail:
        ticket = self._get_ticket(ticket_id)
        requester = self._employee_summaries[ticket.requester_employee_id]
        related_employee = (
            self._employee_summaries[ticket.related_employee_id]
            if ticket.related_employee_id is not None
            else None
        )
        related_device = (
            self._device_summaries[ticket.related_device_id]
            if ticket.related_device_id is not None
            else None
        )
        return HelpdeskTicketDetail(
            ticket=ticket,
            requester=requester,
            related_employee=related_employee,
            related_device=related_device,
        )

    def list_employees(self) -> EmployeeDirectory:
        return EmployeeDirectory(
            seed=self._seed,
            employees=tuple(
                self._directory_employee_records[employee_id]
                for employee_id in sorted(self._directory_employee_records.keys())
            ),
        )

    def get_employee_detail(self, employee_id: str) -> EmployeeDirectoryDetail:
        employee = self._directory_employee_records.get(employee_id)
        if employee is None:
            raise EmployeeNotFoundError(f"employee {employee_id} does not exist")

        manager = (
            self._employee_summaries[employee.manager_employee_id]
            if employee.manager_employee_id is not None
            else None
        )
        devices = tuple(
            device
            for device in self._device_summaries.values()
            if device.employee_id == employee.employee_id
        )
        related_tickets = tuple(
            ticket
            for ticket in self._ticket_records.values()
            if ticket.requester_employee_id == employee.employee_id
            or ticket.related_employee_id == employee.employee_id
        )
        suspicious_events = tuple(
            event
            for event in self._suspicious_event_summaries.values()
            if event.employee_id == employee.employee_id
        )

        return EmployeeDirectoryDetail(
            employee=employee,
            manager=manager,
            devices=devices,
            account_access=self._account_access_summaries[employee.employee_id],
            related_tickets=related_tickets,
            suspicious_events=suspicious_events,
        )

    def list_wiki_documents(self) -> WikiDocumentList:
        return WikiDocumentList(
            seed=self._seed,
            documents=tuple(
                self._wiki_documents[slug] for slug in sorted(self._wiki_documents.keys())
            ),
        )

    def get_wiki_document(self, slug: str) -> WikiDocumentRecord:
        document = self._wiki_documents.get(slug)
        if document is None:
            raise WikiDocumentNotFoundError(f"wiki document {slug} does not exist")
        return document

    def search_wiki_documents(self, query: str) -> WikiSearchResponse:
        terms = tuple(term for term in self._normalize_search_text(query).split() if term)
        if not terms:
            return WikiSearchResponse(seed=self._seed, query=query, results=())

        results: list[WikiSearchResult] = []
        for document in self._wiki_documents.values():
            haystack = self._normalize_search_text(
                " ".join(
                    (
                        document.slug,
                        document.title,
                        document.category,
                        document.summary,
                        document.body,
                    )
                )
            )
            matched_terms = tuple(term for term in terms if term in haystack)
            if not matched_terms:
                continue
            score = len(matched_terms) * 10
            if any(term in self._normalize_search_text(document.title) for term in matched_terms):
                score += 5
            results.append(
                WikiSearchResult(
                    document=document,
                    score=score,
                    matched_terms=matched_terms,
                )
            )

        results.sort(
            key=lambda result: (
                -result.score,
                result.document.title.lower(),
                result.document.slug,
            )
        )
        return WikiSearchResponse(seed=self._seed, query=query, results=tuple(results))

    def list_inbox_threads(self) -> InboxThreadList:
        return InboxThreadList(
            seed=self._seed,
            threads=tuple(
                self._inbox_threads[thread_id] for thread_id in sorted(self._inbox_threads.keys())
            ),
        )

    def get_inbox_thread(self, thread_id: str) -> InboxThreadRecord:
        thread = self._inbox_threads.get(thread_id)
        if thread is None:
            raise InboxThreadNotFoundError(f"inbox thread {thread_id} does not exist")
        return thread

    def get_account_access(self, employee_id: str) -> AccountAccessSummary:
        account = self._account_access_summaries.get(employee_id)
        if account is None:
            raise AccountAccessNotFoundError(f"account access for {employee_id} does not exist")
        return account

    def list_suspicious_events_for_employee(
        self,
        employee_id: str,
    ) -> tuple[SuspiciousEventSummary, ...]:
        return tuple(
            event
            for event in self._suspicious_event_summaries.values()
            if event.employee_id == employee_id
        )

    def update_account_access(
        self,
        employee_id: str,
        *,
        account_locked: bool | None = None,
        mfa_enrolled: bool | None = None,
        groups: tuple[str, ...] | None = None,
        is_admin: bool | None = None,
    ) -> AccountAccessSummary:
        account = self.get_account_access(employee_id)
        updated = account.model_copy(
            update={
                "account_locked": account_locked if account_locked is not None else account.account_locked,
                "mfa_enrolled": mfa_enrolled if mfa_enrolled is not None else account.mfa_enrolled,
                "groups": groups if groups is not None else account.groups,
                "is_admin": is_admin if is_admin is not None else account.is_admin,
                "password_last_reset_at": self._next_mutation_time(),
            }
        )
        self._account_access_summaries[employee_id] = updated
        return updated

    def get_device(self, device_id: str) -> DeviceSummary:
        device = self._device_summaries.get(device_id)
        if device is None:
            raise DeviceNotFoundError(f"device {device_id} does not exist")
        return device

    def update_device(
        self,
        device_id: str,
        *,
        health_state: str | None = None,
        compromised: bool | None = None,
    ) -> DeviceSummary:
        device = self.get_device(device_id)
        updated = device.model_copy(
            update={
                "health_state": health_state if health_state is not None else device.health_state,
                "compromised": compromised if compromised is not None else device.compromised,
                "assigned_at": device.assigned_at,
            }
        )
        self._device_summaries[device_id] = updated
        return updated

    def update_suspicious_event_disposition(
        self,
        event_id: str,
        *,
        disposition: str,
    ) -> SuspiciousEventSummary:
        event = self._suspicious_event_summaries.get(event_id)
        if event is None:
            raise SuspiciousEventNotFoundError(f"suspicious event {event_id} does not exist")
        updated = event.model_copy(update={"disposition": disposition})
        self._suspicious_event_summaries[event_id] = updated
        return updated

    def assign_ticket(self, ticket_id: str, *, assigned_to: str | None) -> HelpdeskTicketRecord:
        ticket = self._get_ticket(ticket_id)
        updated = ticket.model_copy(
            update={
                "assigned_to": assigned_to,
                "updated_at": self._next_mutation_time(),
            }
        )
        self._ticket_records[ticket_id] = updated
        return updated

    def transition_ticket_status(
        self,
        ticket_id: str,
        *,
        status: TicketStatus,
    ) -> HelpdeskTicketRecord:
        ticket = self._get_ticket(ticket_id)
        if status != ticket.status and status not in ALLOWED_STATUS_TRANSITIONS[ticket.status]:
            raise InvalidTicketTransitionError(
                f"ticket {ticket_id} cannot transition from {ticket.status.value} to {status.value}"
            )
        updated = ticket.model_copy(
            update={
                "status": status,
                "updated_at": self._next_mutation_time(),
            }
        )
        self._ticket_records[ticket_id] = updated
        return updated

    def add_note(
        self,
        ticket_id: str,
        *,
        author: str,
        body: str,
        kind: NoteKind = NoteKind.INTERNAL,
    ) -> HelpdeskTicketRecord:
        ticket = self._get_ticket(ticket_id)
        note = TicketNote(
            note_id=f"note_{ticket_id}_{len(ticket.notes) + 1:03d}",
            ticket_id=ticket_id,
            author=author,
            body=body,
            kind=kind,
            created_at=self._next_mutation_time(),
        )
        updated = ticket.model_copy(
            update={
                "notes": (*ticket.notes, note),
                "updated_at": note.created_at,
            }
        )
        self._ticket_records[ticket_id] = updated
        return updated

    def reset(self) -> TicketQueue:
        self._fixture.reset()
        self._mutation_counter = 0
        self._reset_runtime_state()
        return self.list_ticket_queue()

    def rehydrate(self) -> TicketQueue:
        self._fixture.rehydrate()
        self._mutation_counter = 0
        self._reset_runtime_state()
        return self.list_ticket_queue()

    def _reset_runtime_state(self) -> None:
        snapshot = self._fixture.snapshot()
        world = snapshot.base_world
        self._employee_summaries = {
            employee.employee_id: EmployeeSummary(
                employee_id=employee.employee_id,
                display_name=employee.display_name,
                email=employee.email,
                title=employee.title,
                department_slug=employee.department_slug,
                manager_employee_id=employee.manager_employee_id,
            )
            for employee in world.employees
        }
        self._employee_ids_by_email = {
            employee.email: employee.employee_id for employee in world.employees
        }
        self._directory_employee_records = {
            employee.employee_id: DirectoryEmployeeRecord(
                employee_id=employee.employee_id,
                display_name=employee.display_name,
                email=employee.email,
                title=employee.title,
                department_slug=employee.department_slug,
                employment_status=employee.employment_status.value,
                location=employee.location,
                manager_employee_id=employee.manager_employee_id,
                start_date=employee.start_date,
            )
            for employee in world.employees
        }
        self._device_summaries = {
            device.device_id: DeviceSummary(
                device_id=device.device_id,
                employee_id=device.employee_id,
                hostname=device.hostname,
                platform=device.platform.value,
                health_state=device.health_state,
                compromised=device.compromised,
                assigned_at=device.assigned_at,
                serial_number=device.serial_number,
            )
            for device in world.devices
        }
        self._account_access_summaries = {
            account.employee_id: AccountAccessSummary(
                account_id=account.account_id,
                email=account.email,
                account_locked=account.account_locked,
                mfa_enrolled=account.mfa_enrolled,
                groups=account.groups,
                is_admin=account.is_admin,
                password_last_reset_at=account.password_last_reset_at,
            )
            for account in world.account_access_states
        }
        self._suspicious_event_summaries = {
            event.event_id: SuspiciousEventSummary(
                event_id=event.event_id,
                employee_id=event.employee_id,
                detected_at=event.detected_at,
                signal_type=event.signal_type,
                severity=event.severity,
                summary=event.summary,
                disposition=event.disposition.value,
            )
            for event in world.suspicious_events
        }
        self._ticket_records = {
            ticket.ticket_id: HelpdeskTicketRecord(
                ticket_id=ticket.ticket_id,
                requester_employee_id=ticket.requester_employee_id,
                assigned_team=ticket.assigned_team,
                status=ticket.status,
                priority=ticket.priority.value,
                title=ticket.title,
                summary=ticket.summary,
                created_at=ticket.created_at,
                updated_at=ticket.created_at,
                related_employee_id=ticket.related_employee_id,
                related_device_id=ticket.related_device_id,
                tags=ticket.tags,
            )
            for ticket in world.tickets
        }
        self._wiki_documents = {
            page.slug: WikiDocumentRecord(
                page_id=page.page_id,
                slug=page.slug,
                title=page.title,
                category=page.category.value,
                summary=page.summary,
                body=page.body,
                updated_at=page.updated_at,
            )
            for page in world.wiki_pages
        }
        self._inbox_threads = {
            thread.thread_id: InboxThreadRecord(
                thread_id=thread.thread_id,
                participant_emails=thread.participant_emails,
                subject=thread.subject,
                messages=tuple(
                    InboxMessageRecord(
                        message_id=message.message_id,
                        sender=message.sender,
                        sent_at=message.sent_at,
                        subject=message.subject,
                        body=message.body,
                        channel=message.channel.value,
                    )
                    for message in thread.messages
                ),
                last_message_at=max(message.sent_at for message in thread.messages),
                message_count=len(thread.messages),
            )
            for thread in world.inbox_threads
        }

    def _get_ticket(self, ticket_id: str) -> HelpdeskTicketRecord:
        ticket = self._ticket_records.get(ticket_id)
        if ticket is None:
            raise HelpdeskTicketNotFoundError(f"ticket {ticket_id} does not exist")
        return ticket

    def _next_mutation_time(self) -> datetime:
        self._mutation_counter += 1
        return BASE_TIME + timedelta(seconds=self._mutation_counter)

    @staticmethod
    def _normalize_search_text(value: str) -> str:
        normalized = "".join(character.lower() if character.isalnum() else " " for character in value)
        return " ".join(normalized.split())
