from __future__ import annotations

from dataclasses import dataclass

from atlas_core import (
    ToolExecutionMetadata,
    ToolExecutor,
    ToolRequest,
    ToolResult,
    ToolResultOutcome,
    ToolSpec,
)


class ToolRegistryError(Exception):
    """Base error for worker tool registry operations."""


class DuplicateToolError(ToolRegistryError):
    """Raised when attempting to register a duplicate tool name."""


class UnknownToolError(ToolRegistryError):
    """Raised when a tool name cannot be resolved."""


@dataclass(frozen=True)
class RegisteredTool:
    spec: ToolSpec
    executor: ToolExecutor


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, spec: ToolSpec, executor: ToolExecutor) -> None:
        if spec.name in self._tools:
            raise DuplicateToolError(f"tool {spec.name} is already registered")
        self._tools[spec.name] = RegisteredTool(spec=spec, executor=executor)

    def get_spec(self, name: str) -> ToolSpec:
        return self._get_registered(name).spec

    def resolve(self, name: str) -> RegisteredTool:
        return self._get_registered(name)

    def list_specs(self) -> tuple[ToolSpec, ...]:
        return tuple(self._tools[name].spec for name in sorted(self._tools.keys()))

    def execute(self, request: ToolRequest) -> ToolResult:
        # Utility-only surface for focused executor tests. The live agent path
        # resolves tool specs here but executes through Bastion from the worker loop.
        return self._get_registered(request.tool_name).executor.execute(request)

    def _get_registered(self, name: str) -> RegisteredTool:
        registered = self._tools.get(name)
        if registered is None:
            raise UnknownToolError(f"tool {name} is not registered")
        return registered


class PlaceholderToolExecutor:
    def execute(self, request: ToolRequest) -> ToolResult:
        return ToolResult(
            request_id=request.request_id,
            tool_name=request.tool_name,
            outcome=ToolResultOutcome.FATAL_ERROR,
            error_message=f"tool {request.tool_name} is registered but not implemented yet",
            metadata={"placeholder": True},
        )


def build_phase4_tool_registry() -> ToolRegistry:
    return build_phase4_tool_registry_with_browser()


def build_phase4_tool_registry_with_browser(
    *,
    browser_executor: ToolExecutor | None = None,
    helpdesk_ticket_executor: ToolExecutor | None = None,
    document_lookup_executor: ToolExecutor | None = None,
    directory_lookup_executor: ToolExecutor | None = None,
    identity_api_executor: ToolExecutor | None = None,
    screenshot_capture_executor: ToolExecutor | None = None,
) -> ToolRegistry:
    registry = ToolRegistry()
    placeholder = PlaceholderToolExecutor()

    for spec in _phase4_tool_specs():
        if spec.name == "browser" and browser_executor is not None:
            executor = browser_executor
        elif spec.name == "helpdesk_ticket" and helpdesk_ticket_executor is not None:
            executor = helpdesk_ticket_executor
        elif spec.name == "document_lookup" and document_lookup_executor is not None:
            executor = document_lookup_executor
        elif spec.name == "directory_lookup" and directory_lookup_executor is not None:
            executor = directory_lookup_executor
        elif spec.name == "identity_api" and identity_api_executor is not None:
            executor = identity_api_executor
        elif spec.name == "screenshot_capture" and screenshot_capture_executor is not None:
            executor = screenshot_capture_executor
        else:
            executor = placeholder
        registry.register(spec, executor)

    return registry


def _phase4_tool_specs() -> tuple[ToolSpec, ...]:
    return (
        ToolSpec(
            name="browser",
            description="Navigate and inspect local seeded internal app surfaces.",
            input_schema={
                "type": "object",
                "required": ["action"],
                "properties": {
                    "action": {"type": "string"},
                    "target": {"type": "string"},
                    "value": {"type": "string"},
                },
            },
            result_schema={
                "type": "object",
                "properties": {
                    "pageSummary": {"type": "string"},
                    "extractedText": {"type": "string"},
                },
            },
            execution_metadata=ToolExecutionMetadata(
                read_only=False,
                idempotent=False,
                requires_browser=True,
                timeout_seconds=45,
                tags=("phase4", "browser"),
            ),
        ),
        ToolSpec(
            name="helpdesk_ticket",
            description="Read and update seeded helpdesk ticket state.",
            input_schema={
                "type": "object",
                "required": ["action"],
                "properties": {
                    "action": {"type": "string"},
                    "ticket_id": {"type": "string"},
                    "author": {"type": "string"},
                    "note_body": {"type": "string"},
                    "note_kind": {"type": "string"},
                    "status": {"type": "string"},
                    "assigned_to": {"type": "string"},
                },
            },
            result_schema={
                "type": "object",
                "properties": {
                    "ticket": {"type": "object"},
                    "detail": {"type": "object"},
                    "queue": {"type": "object"},
                    "change_set": {"type": "object"},
                    "matched_ticket_ids": {"type": "array", "items": {"type": "string"}},
                },
            },
            execution_metadata=ToolExecutionMetadata(
                read_only=False,
                idempotent=False,
                requires_browser=False,
                timeout_seconds=15,
                tags=("phase4", "helpdesk"),
            ),
        ),
        ToolSpec(
            name="document_lookup",
            description="Search and fetch internal wiki documents from the seeded environment.",
            input_schema={
                "type": "object",
                "required": ["action"],
                "properties": {
                    "action": {"type": "string"},
                    "query": {"type": "string"},
                    "slug": {"type": "string"},
                },
            },
            result_schema={
                "type": "object",
                "properties": {
                    "slug": {"type": "string"},
                    "title": {"type": "string"},
                    "matchedTerms": {"type": "array", "items": {"type": "string"}},
                },
            },
            execution_metadata=ToolExecutionMetadata(
                read_only=True,
                idempotent=True,
                requires_browser=False,
                timeout_seconds=10,
                tags=("phase4", "wiki"),
            ),
        ),
        ToolSpec(
            name="directory_lookup",
            description="Look up seeded employee, manager, device, and account context.",
            input_schema={
                "type": "object",
                "required": ["action"],
                "properties": {
                    "action": {"type": "string"},
                    "employee_id": {"type": "string"},
                    "email": {"type": "string"},
                    "name": {"type": "string"},
                    "department_slug": {"type": "string"},
                    "title": {"type": "string"},
                },
            },
            result_schema={
                "type": "object",
                "properties": {
                    "detail": {"type": "object"},
                    "matches": {"type": "array", "items": {"type": "object"}},
                    "matched_employee_ids": {"type": "array", "items": {"type": "string"}},
                },
            },
            execution_metadata=ToolExecutionMetadata(
                read_only=True,
                idempotent=True,
                requires_browser=False,
                timeout_seconds=10,
                tags=("phase4", "directory"),
            ),
        ),
        ToolSpec(
            name="identity_api",
            description="Inspect or apply narrow seeded account-access recovery actions.",
            input_schema={
                "type": "object",
                "required": ["action", "employee_id"],
                "properties": {
                    "action": {"type": "string"},
                    "employee_id": {"type": "string"},
                },
            },
            result_schema={
                "type": "object",
                "properties": {
                    "account_access": {"type": "object"},
                    "change_set": {"type": "object"},
                    "executed_action_marker": {"type": "string"},
                },
            },
            execution_metadata=ToolExecutionMetadata(
                read_only=False,
                idempotent=False,
                requires_browser=False,
                timeout_seconds=15,
                tags=("phase5", "identity"),
            ),
        ),
        ToolSpec(
            name="screenshot_capture",
            description="Capture a browser screenshot and attach it as a run artifact.",
            input_schema={
                "type": "object",
                "required": ["scope"],
                "properties": {
                    "scope": {"type": "string"},
                    "label": {"type": "string"},
                },
            },
            result_schema={
                "type": "object",
                "properties": {
                    "artifactId": {"type": "string"},
                    "uri": {"type": "string"},
                },
            },
            execution_metadata=ToolExecutionMetadata(
                read_only=True,
                idempotent=False,
                requires_browser=True,
                timeout_seconds=20,
                tags=("phase4", "artifact"),
            ),
        ),
    )
