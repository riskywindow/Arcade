from __future__ import annotations

from atlas_core import ToolRequest, ToolResult, ToolResultOutcome
from atlas_env_helpdesk import (
    DocumentLookupAdapter,
    DocumentLookupRequest,
    HelpdeskService,
)


class DocumentLookupToolExecutor:
    def __init__(self, service: HelpdeskService) -> None:
        self._adapter = DocumentLookupAdapter(service)

    def execute(self, request: ToolRequest) -> ToolResult:
        try:
            tool_request = DocumentLookupRequest.model_validate(request.arguments)
        except Exception as exc:
            return ToolResult(
                request_id=request.request_id,
                tool_name=request.tool_name,
                outcome=ToolResultOutcome.INVALID_REQUEST,
                error_message=str(exc),
            )

        try:
            result = self._adapter.execute(tool_request)
        except Exception as exc:
            return ToolResult(
                request_id=request.request_id,
                tool_name=request.tool_name,
                outcome=ToolResultOutcome.FATAL_ERROR,
                error_message=str(exc),
            )

        return ToolResult(
            request_id=request.request_id,
            tool_name=request.tool_name,
            outcome=ToolResultOutcome.SUCCESS,
            result=result.model_dump(mode="json"),
            metadata={
                "action": result.action.value,
                "matchedSlugs": list(result.matched_slugs),
            },
        )
