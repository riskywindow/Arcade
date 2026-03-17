from __future__ import annotations

from enum import StrEnum

from pydantic import model_validator

from atlas_env_helpdesk.contracts import HelpdeskModel
from atlas_env_helpdesk.catalog import list_scenarios
from atlas_env_helpdesk.service import (
    HelpdeskTicketNotFoundError,
    HelpdeskService,
    HelpdeskTicketDetail,
    HelpdeskTicketRecord,
    NoteKind,
    TicketQueue,
)
from atlas_synth import TicketStatus


class HelpdeskTicketToolAction(StrEnum):
    LIST_TICKETS = "list_tickets"
    GET_TICKET = "get_ticket"
    ADD_NOTE = "add_note"
    UPDATE_STATUS = "update_status"
    ASSIGN_TICKET = "assign_ticket"


class HelpdeskTicketToolRequest(HelpdeskModel):
    action: HelpdeskTicketToolAction
    ticket_id: str | None = None
    query: str | None = None
    author: str | None = None
    note_body: str | None = None
    note_kind: NoteKind = NoteKind.INTERNAL
    status: TicketStatus | None = None
    assigned_to: str | None = None

    @model_validator(mode="after")
    def validate_action_requirements(self) -> "HelpdeskTicketToolRequest":
        if self.action == HelpdeskTicketToolAction.GET_TICKET and self.ticket_id is None:
            raise ValueError("get_ticket requires ticket_id")
        if self.action == HelpdeskTicketToolAction.ADD_NOTE:
            if self.ticket_id is None or self.author is None or self.note_body is None:
                raise ValueError("add_note requires ticket_id, author, and note_body")
        if self.action == HelpdeskTicketToolAction.UPDATE_STATUS:
            if self.ticket_id is None or self.status is None:
                raise ValueError("update_status requires ticket_id and status")
        if self.action == HelpdeskTicketToolAction.ASSIGN_TICKET and self.ticket_id is None:
            raise ValueError("assign_ticket requires ticket_id")
        return self


class HelpdeskTicketChangeSet(HelpdeskModel):
    changed_fields: tuple[str, ...] = ()
    previous_status: str | None = None
    new_status: str | None = None
    note_count_before: int | None = None
    note_count_after: int | None = None
    previous_assigned_to: str | None = None
    new_assigned_to: str | None = None


class HelpdeskTicketToolResult(HelpdeskModel):
    action: HelpdeskTicketToolAction
    queue: TicketQueue | None = None
    ticket: HelpdeskTicketRecord | None = None
    detail: HelpdeskTicketDetail | None = None
    change_set: HelpdeskTicketChangeSet | None = None
    matched_ticket_ids: tuple[str, ...] = ()


class HelpdeskTicketToolAdapter:
    def __init__(self, service: HelpdeskService) -> None:
        self._service = service

    def execute(self, request: HelpdeskTicketToolRequest) -> HelpdeskTicketToolResult:
        if request.action == HelpdeskTicketToolAction.LIST_TICKETS:
            queue = self._service.list_ticket_queue()
            if request.query:
                filtered = tuple(
                    ticket
                    for ticket in queue.tickets
                    if self._matches_query(ticket, request.query)
                )
                queue = queue.model_copy(update={"tickets": filtered})
            return HelpdeskTicketToolResult(
                action=request.action,
                queue=queue,
                matched_ticket_ids=tuple(ticket.ticket_id for ticket in queue.tickets),
            )

        if request.action == HelpdeskTicketToolAction.GET_TICKET:
            detail = self._service.get_ticket_detail(self._resolve_ticket_id(request.ticket_id))
            return HelpdeskTicketToolResult(
                action=request.action,
                ticket=detail.ticket,
                detail=detail,
                matched_ticket_ids=(detail.ticket.ticket_id,),
            )

        if request.action == HelpdeskTicketToolAction.ADD_NOTE:
            ticket_id = self._resolve_ticket_id(request.ticket_id)
            before = self._service.get_ticket_detail(ticket_id).ticket
            ticket = self._service.add_note(
                ticket_id,
                author=request.author or "",
                body=request.note_body or "",
                kind=request.note_kind,
            )
            return HelpdeskTicketToolResult(
                action=request.action,
                ticket=ticket,
                change_set=HelpdeskTicketChangeSet(
                    changed_fields=("notes", "updated_at"),
                    note_count_before=len(before.notes),
                    note_count_after=len(ticket.notes),
                ),
                matched_ticket_ids=(ticket.ticket_id,),
            )

        if request.action == HelpdeskTicketToolAction.UPDATE_STATUS:
            ticket_id = self._resolve_ticket_id(request.ticket_id)
            before = self._service.get_ticket_detail(ticket_id).ticket
            ticket = self._service.transition_ticket_status(
                ticket_id,
                status=request.status or before.status,
            )
            return HelpdeskTicketToolResult(
                action=request.action,
                ticket=ticket,
                change_set=HelpdeskTicketChangeSet(
                    changed_fields=("status", "updated_at"),
                    previous_status=before.status.value,
                    new_status=ticket.status.value,
                ),
                matched_ticket_ids=(ticket.ticket_id,),
            )

        ticket_id = self._resolve_ticket_id(request.ticket_id)
        before = self._service.get_ticket_detail(ticket_id).ticket
        ticket = self._service.assign_ticket(
            ticket_id,
            assigned_to=request.assigned_to,
        )
        return HelpdeskTicketToolResult(
            action=request.action,
            ticket=ticket,
            change_set=HelpdeskTicketChangeSet(
                changed_fields=("assigned_to", "updated_at"),
                previous_assigned_to=before.assigned_to,
                new_assigned_to=ticket.assigned_to,
            ),
            matched_ticket_ids=(ticket.ticket_id,),
        )

    @staticmethod
    def _matches_query(ticket: HelpdeskTicketRecord, query: str) -> bool:
        needle = query.strip().lower()
        if not needle:
            return True
        haystack = " ".join(
            (
                ticket.ticket_id,
                ticket.title,
                ticket.summary,
                " ".join(ticket.tags),
            )
        ).lower()
        return needle in haystack

    def _resolve_ticket_id(self, ticket_id: str | None) -> str:
        candidate = ticket_id or ""
        try:
            self._service.get_ticket_detail(candidate)
            return candidate
        except HelpdeskTicketNotFoundError:
            pass

        scenario_by_visible_id = {
            scenario.public_task.visible_ticket.ticket_id: scenario.public_task.visible_ticket.title
            for scenario in list_scenarios()
        }
        title = scenario_by_visible_id.get(candidate)
        if title is None:
            raise HelpdeskTicketNotFoundError(f"ticket {candidate} does not exist")
        for ticket in self._service.list_ticket_queue().tickets:
            if ticket.title == title:
                return ticket.ticket_id
        raise HelpdeskTicketNotFoundError(f"ticket {candidate} does not exist")
