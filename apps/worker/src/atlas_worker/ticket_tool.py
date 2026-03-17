from __future__ import annotations

from atlas_core import SecretHandle, ToolRequest, ToolResult, ToolResultOutcome
from atlas_env_helpdesk import (
    HelpdeskService,
    HelpdeskTicketToolAdapter,
    HelpdeskTicketToolRequest,
)


class HelpdeskTicketToolExecutor:
    def __init__(self, service: HelpdeskService) -> None:
        self._adapter = HelpdeskTicketToolAdapter(service)

    def execute(self, request: ToolRequest) -> ToolResult:
        try:
            tool_request = HelpdeskTicketToolRequest.model_validate(request.arguments)
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

        payload = result.model_dump(mode="json")
        return ToolResult(
            request_id=request.request_id,
            tool_name=request.tool_name,
            outcome=ToolResultOutcome.SUCCESS,
            result=payload,
            metadata={
                "matchedTicketIds": list(result.matched_ticket_ids),
                "action": result.action.value,
            },
        )

    def execute_with_secrets(
        self,
        request: ToolRequest,
        *,
        resolved_secrets: dict[str, str],
        secret_handles: tuple[SecretHandle, ...],
    ) -> ToolResult:
        action = request.arguments.get("action")
        if action in {"add_note", "assign_ticket", "update_status"}:
            expected_handle = "secret://bastion/helpdesk-mutation-token"
            token = resolved_secrets.get(expected_handle)
            if token != "atlas-local-helpdesk-mutation-token":
                return ToolResult(
                    request_id=request.request_id,
                    tool_name=request.tool_name,
                    outcome=ToolResultOutcome.FATAL_ERROR,
                    error_message="missing scoped helpdesk mutation credential",
                )

        result = self.execute(request)
        if result.outcome != ToolResultOutcome.SUCCESS or not secret_handles:
            return result

        return result.model_copy(
            update={
                "metadata": {
                    **result.metadata,
                    "credentialHandle": secret_handles[0].handle,
                    "credentialScope": secret_handles[0].scope,
                }
            }
        )
