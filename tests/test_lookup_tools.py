from __future__ import annotations

from atlas_core import ToolRequest, ToolResultOutcome
from atlas_env_helpdesk import (
    DirectoryLookupAction,
    DirectoryLookupAdapter,
    DirectoryLookupRequest,
    DocumentLookupAction,
    DocumentLookupAdapter,
    DocumentLookupRequest,
    HelpdeskService,
)
from atlas_worker import (
    DirectoryLookupToolExecutor,
    DocumentLookupToolExecutor,
    build_phase4_tool_registry_with_browser,
)


def test_document_lookup_adapter_searches_and_fetches_seeded_docs() -> None:
    service = HelpdeskService.seeded("seed-phase3-demo")
    adapter = DocumentLookupAdapter(service)

    search_result = adapter.execute(
        DocumentLookupRequest(
            action=DocumentLookupAction.SEARCH_DOCUMENTS,
            query="travel mfa",
        )
    )
    assert search_result.results
    assert search_result.results[0].document.slug == "travel-lockout-recovery"

    get_result = adapter.execute(
        DocumentLookupRequest(
            action=DocumentLookupAction.GET_DOCUMENT,
            slug="travel-lockout-recovery",
        )
    )
    assert get_result.document is not None
    assert get_result.document.title == "Travel Lockout Recovery SOP"


def test_directory_lookup_adapter_supports_name_email_and_detail_queries() -> None:
    service = HelpdeskService.seeded("seed-phase3-demo")
    adapter = DirectoryLookupAdapter(service)

    name_result = adapter.execute(
        DirectoryLookupRequest(
            action=DirectoryLookupAction.SEARCH_EMPLOYEES,
            name="Tessa",
        )
    )
    assert name_result.matches
    assert name_result.matches[0].employee.email == "tessa.nguyen@northstar-health.example"
    assert "name" in name_result.matches[0].match_reasons

    email_result = adapter.execute(
        DirectoryLookupRequest(
            action=DirectoryLookupAction.SEARCH_EMPLOYEES,
            email="tessa.nguyen@northstar-health.example",
        )
    )
    assert len(email_result.matched_employee_ids) == 1
    assert email_result.matches[0].employee.email == "tessa.nguyen@northstar-health.example"

    detail_result = adapter.execute(
        DirectoryLookupRequest(
            action=DirectoryLookupAction.GET_EMPLOYEE_DETAIL,
            employee_id=email_result.matched_employee_ids[0],
        )
    )
    assert detail_result.detail is not None
    assert detail_result.detail.manager is not None
    assert detail_result.detail.devices


def test_directory_lookup_adapter_returns_stable_order_for_ambiguous_matches() -> None:
    service = HelpdeskService.seeded("seed-phase3-demo")
    adapter = DirectoryLookupAdapter(service)

    result = adapter.execute(
        DirectoryLookupRequest(
            action=DirectoryLookupAction.SEARCH_EMPLOYEES,
            title="analyst",
        )
    )

    display_names = [match.employee.display_name for match in result.matches]
    assert display_names == sorted(display_names, key=str.lower)


def test_document_and_directory_tool_executors_are_registry_callable() -> None:
    service = HelpdeskService.seeded("seed-phase3-demo")
    registry = build_phase4_tool_registry_with_browser(
        document_lookup_executor=DocumentLookupToolExecutor(service),
        directory_lookup_executor=DirectoryLookupToolExecutor(service),
    )

    doc_result = registry.execute(
        ToolRequest(
            request_id="toolreq_doc_001",
            tool_name="document_lookup",
            arguments={"action": "search_documents", "query": "mfa device loss"},
        )
    )
    assert doc_result.outcome == ToolResultOutcome.SUCCESS
    assert doc_result.metadata["action"] == "search_documents"

    directory_result = registry.execute(
        ToolRequest(
            request_id="toolreq_dir_001",
            tool_name="directory_lookup",
            arguments={"action": "search_employees", "department_slug": "finance"},
        )
    )
    assert directory_result.outcome == ToolResultOutcome.SUCCESS
    assert directory_result.metadata["action"] == "search_employees"


def test_directory_lookup_executor_rejects_missing_search_criteria() -> None:
    executor = DirectoryLookupToolExecutor(HelpdeskService.seeded("seed-phase3-demo"))

    result = executor.execute(
        ToolRequest(
            request_id="toolreq_dir_bad",
            tool_name="directory_lookup",
            arguments={"action": "search_employees"},
        )
    )

    assert result.outcome == ToolResultOutcome.INVALID_REQUEST
