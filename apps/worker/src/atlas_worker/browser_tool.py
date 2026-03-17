from __future__ import annotations

from browser_runner import (
    BrowserAction,
    BrowserAutomationRunner,
    BrowserCommand,
    BrowserRunnerConfig,
    BrowserRunnerConfigError,
    BrowserRunnerError,
    PlaywrightBrowserRunner,
)

from atlas_core import ToolRequest, ToolResult, ToolResultOutcome


class BrowserToolExecutor:
    def __init__(self, runner: BrowserAutomationRunner | None = None) -> None:
        self._runner = runner or PlaywrightBrowserRunner(BrowserRunnerConfig())

    def execute(self, request: ToolRequest) -> ToolResult:
        action_value = request.arguments.get("action")
        if not isinstance(action_value, str):
            return ToolResult(
                request_id=request.request_id,
                tool_name=request.tool_name,
                outcome=ToolResultOutcome.INVALID_REQUEST,
                error_message="browser tool requires a string action argument",
            )

        target_value = request.arguments.get("target")
        if target_value is not None and not isinstance(target_value, str):
            return ToolResult(
                request_id=request.request_id,
                tool_name=request.tool_name,
                outcome=ToolResultOutcome.INVALID_REQUEST,
                error_message="browser tool target must be a string when provided",
            )

        value = request.arguments.get("value")
        if value is not None and not isinstance(value, str):
            return ToolResult(
                request_id=request.request_id,
                tool_name=request.tool_name,
                outcome=ToolResultOutcome.INVALID_REQUEST,
                error_message="browser tool value must be a string when provided",
            )

        try:
            command = BrowserCommand(
                action=BrowserAction(action_value),
                target=target_value,
                value=value,
            )
        except ValueError:
            return ToolResult(
                request_id=request.request_id,
                tool_name=request.tool_name,
                outcome=ToolResultOutcome.INVALID_REQUEST,
                error_message=f"unsupported browser action {action_value}",
            )

        try:
            observation = self._runner.run(command)
        except BrowserRunnerConfigError as exc:
            return ToolResult(
                request_id=request.request_id,
                tool_name=request.tool_name,
                outcome=ToolResultOutcome.INVALID_REQUEST,
                error_message=str(exc),
            )
        except BrowserRunnerError as exc:
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
            result={
                "currentUrl": observation.current_url,
                "title": observation.title,
                "pageSummary": observation.page_summary,
                "extractedText": observation.extracted_text,
                "visibleTestIds": list(observation.visible_test_ids),
            },
        )

    def close(self) -> None:
        self._runner.close()
