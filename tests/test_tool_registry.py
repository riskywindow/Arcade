from __future__ import annotations

from pathlib import Path

import pytest

from atlas_core import (
    ToolExecutionMetadata,
    ToolRequest,
    ToolResult,
    ToolResultOutcome,
    ToolSpec,
)
from atlas_worker import (
    DuplicateToolError,
    ToolRegistry,
    UnknownToolError,
    build_phase4_tool_registry,
)


class _EchoExecutor:
    def execute(self, request: ToolRequest) -> ToolResult:
        return ToolResult(
            request_id=request.request_id,
            tool_name=request.tool_name,
            outcome=ToolResultOutcome.SUCCESS,
            result={"echo": request.arguments},
        )


def test_tool_spec_round_trips_through_json() -> None:
    spec = ToolSpec(
        name="document_lookup",
        description="Search internal wiki docs.",
        input_schema={"type": "object", "required": ["query"]},
        result_schema={"type": "object", "properties": {"slug": {"type": "string"}}},
        execution_metadata=ToolExecutionMetadata(
            read_only=True,
            idempotent=True,
            timeout_seconds=10,
            tags=("phase4", "wiki"),
        ),
    )

    assert ToolSpec.model_validate_json(spec.model_dump_json()) == spec


def test_registry_registers_and_executes_tool_request() -> None:
    registry = ToolRegistry()
    spec = ToolSpec(
        name="document_lookup",
        description="Search internal wiki docs.",
    )
    registry.register(spec, _EchoExecutor())

    result = registry.execute(
        ToolRequest(
            request_id="toolreq_001",
            tool_name="document_lookup",
            arguments={"query": "mfa device loss"},
        )
    )

    assert registry.get_spec("document_lookup") == spec
    assert result.outcome == ToolResultOutcome.SUCCESS
    assert result.result == {"echo": {"query": "mfa device loss"}}


def test_registry_can_resolve_registered_tool_without_execution() -> None:
    registry = ToolRegistry()
    spec = ToolSpec(name="document_lookup", description="Search internal wiki docs.")
    executor = _EchoExecutor()
    registry.register(spec, executor)

    registered = registry.resolve("document_lookup")

    assert registered.spec == spec
    assert registered.executor is executor


def test_registry_rejects_duplicate_tool_names() -> None:
    registry = ToolRegistry()
    spec = ToolSpec(name="browser", description="Inspect internal apps.")
    registry.register(spec, _EchoExecutor())

    with pytest.raises(DuplicateToolError):
        registry.register(spec, _EchoExecutor())


def test_registry_rejects_unknown_tool_names() -> None:
    registry = ToolRegistry()

    with pytest.raises(UnknownToolError):
        registry.get_spec("browser")

    with pytest.raises(UnknownToolError):
        registry.execute(
            ToolRequest(
                request_id="toolreq_missing",
                tool_name="browser",
                arguments={"action": "open"},
            )
        )


def test_phase4_tool_registry_registers_expected_tools_and_placeholder_errors() -> None:
    registry = build_phase4_tool_registry()

    specs = registry.list_specs()
    assert [spec.name for spec in specs] == [
        "browser",
        "directory_lookup",
        "document_lookup",
        "helpdesk_ticket",
        "identity_api",
        "screenshot_capture",
    ]

    result = registry.execute(
        ToolRequest(
            request_id="toolreq_placeholder",
            tool_name="browser",
            arguments={"action": "open", "target": "/internal/helpdesk"},
        )
    )
    assert result.outcome == ToolResultOutcome.FATAL_ERROR
    assert result.metadata["placeholder"] is True


def test_shared_types_export_phase_four_tool_contracts() -> None:
    source = Path("packages/shared-types/src/index.ts").read_text(encoding="utf-8")

    required_exports = (
        "export type ToolExecutionMetadata",
        "export type ToolSpec",
    )

    for export_name in required_exports:
        assert export_name in source
