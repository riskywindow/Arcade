from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from atlas_env_helpdesk.contracts import HelpdeskModel
from atlas_env_helpdesk.service import (
    DirectoryEmployeeRecord,
    EmployeeDirectoryDetail,
    HelpdeskService,
    WikiDocumentRecord,
    WikiSearchResult,
)


class DocumentLookupAction(StrEnum):
    SEARCH_DOCUMENTS = "search_documents"
    GET_DOCUMENT = "get_document"


class DocumentLookupRequest(HelpdeskModel):
    action: DocumentLookupAction
    query: str | None = None
    slug: str | None = None

    @model_validator(mode="after")
    def validate_action_requirements(self) -> "DocumentLookupRequest":
        if self.action == DocumentLookupAction.SEARCH_DOCUMENTS and not self.query:
            raise ValueError("search_documents requires query")
        if self.action == DocumentLookupAction.GET_DOCUMENT and not self.slug:
            raise ValueError("get_document requires slug")
        return self


class DocumentLookupResult(HelpdeskModel):
    action: DocumentLookupAction
    query: str | None = None
    document: WikiDocumentRecord | None = None
    results: tuple[WikiSearchResult, ...] = ()
    matched_slugs: tuple[str, ...] = ()


class DocumentLookupAdapter:
    def __init__(self, service: HelpdeskService) -> None:
        self._service = service

    def execute(self, request: DocumentLookupRequest) -> DocumentLookupResult:
        if request.action == DocumentLookupAction.SEARCH_DOCUMENTS:
            response = self._service.search_wiki_documents(request.query or "")
            return DocumentLookupResult(
                action=request.action,
                query=response.query,
                results=response.results,
                matched_slugs=tuple(result.document.slug for result in response.results),
            )

        document = self._service.get_wiki_document(request.slug or "")
        return DocumentLookupResult(
            action=request.action,
            document=document,
            matched_slugs=(document.slug,),
        )


class DirectoryLookupAction(StrEnum):
    SEARCH_EMPLOYEES = "search_employees"
    GET_EMPLOYEE_DETAIL = "get_employee_detail"


class DirectoryLookupRequest(HelpdeskModel):
    action: DirectoryLookupAction
    employee_id: str | None = None
    email: str | None = None
    name: str | None = None
    department_slug: str | None = None
    title: str | None = None

    @model_validator(mode="after")
    def validate_action_requirements(self) -> "DirectoryLookupRequest":
        if self.action == DirectoryLookupAction.GET_EMPLOYEE_DETAIL and not self.employee_id:
            raise ValueError("get_employee_detail requires employee_id")
        if self.action == DirectoryLookupAction.SEARCH_EMPLOYEES:
            if not any(
                value
                for value in (
                    self.employee_id,
                    self.email,
                    self.name,
                    self.department_slug,
                    self.title,
                )
            ):
                raise ValueError(
                    "search_employees requires at least one of employee_id, email, name, department_slug, or title"
                )
        return self


class DirectoryLookupMatch(HelpdeskModel):
    employee: DirectoryEmployeeRecord
    match_reasons: tuple[str, ...] = ()


class DirectoryLookupResult(HelpdeskModel):
    action: DirectoryLookupAction
    detail: EmployeeDirectoryDetail | None = None
    matches: tuple[DirectoryLookupMatch, ...] = ()
    matched_employee_ids: tuple[str, ...] = ()


class DirectoryLookupAdapter:
    def __init__(self, service: HelpdeskService) -> None:
        self._service = service

    def execute(self, request: DirectoryLookupRequest) -> DirectoryLookupResult:
        if request.action == DirectoryLookupAction.GET_EMPLOYEE_DETAIL:
            detail = self._service.get_employee_detail(request.employee_id or "")
            return DirectoryLookupResult(
                action=request.action,
                detail=detail,
                matched_employee_ids=(detail.employee.employee_id,),
            )

        matches: list[DirectoryLookupMatch] = []
        for employee in self._service.list_employees().employees:
            reasons = self._match_reasons(employee, request)
            if reasons:
                matches.append(DirectoryLookupMatch(employee=employee, match_reasons=reasons))

        matches.sort(
            key=lambda match: (
                match.employee.display_name.lower(),
                match.employee.employee_id,
            )
        )
        return DirectoryLookupResult(
            action=request.action,
            matches=tuple(matches),
            matched_employee_ids=tuple(match.employee.employee_id for match in matches),
        )

    @staticmethod
    def _match_reasons(
        employee: DirectoryEmployeeRecord,
        request: DirectoryLookupRequest,
    ) -> tuple[str, ...]:
        reasons: list[str] = []
        if request.employee_id and employee.employee_id == request.employee_id:
            reasons.append("employee_id")
        if request.email and employee.email.lower() == request.email.lower():
            reasons.append("email")
        if request.name and request.name.lower() in employee.display_name.lower():
            reasons.append("name")
        if request.department_slug and request.department_slug.lower() == employee.department_slug.lower():
            reasons.append("department_slug")
        if request.title and request.title.lower() in employee.title.lower():
            reasons.append("title")
        return tuple(reasons)
