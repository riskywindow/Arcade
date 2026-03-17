from __future__ import annotations

from atlas_core import ToolRequest, ToolResultOutcome
from atlas_worker import BrowserToolExecutor, build_phase4_tool_registry_with_browser
from browser_runner import BrowserAction, BrowserCommand, BrowserObservation


class _FakeBrowserRunner:
    def __init__(self) -> None:
        self.commands: list[BrowserCommand] = []

    def run(self, command: BrowserCommand) -> BrowserObservation:
        self.commands.append(command)
        return BrowserObservation(
            current_url="http://127.0.0.1:3000/internal/helpdesk",
            title="Helpdesk Queue",
            page_summary="Helpdesk Queue | Internal App | Helpdesk Queue",
            extracted_text="Helpdesk Queue Travel login lockout after phone replacement",
            visible_test_ids=("nav-link-helpdesk", "ticket-link-ticket_travel_lockout_recovery"),
        )

    def close(self) -> None:
        return None


def test_browser_tool_executor_returns_successful_observation() -> None:
    runner = _FakeBrowserRunner()
    executor = BrowserToolExecutor(runner)

    result = executor.execute(
        ToolRequest(
            request_id="toolreq_browser_001",
            tool_name="browser",
            arguments={"action": "open", "target": "/internal/helpdesk"},
        )
    )

    assert result.outcome == ToolResultOutcome.SUCCESS
    assert result.result is not None
    assert result.result["title"] == "Helpdesk Queue"
    assert runner.commands[0].action == BrowserAction.OPEN


def test_browser_tool_executor_rejects_invalid_request_shapes() -> None:
    executor = BrowserToolExecutor(_FakeBrowserRunner())

    result = executor.execute(
        ToolRequest(
            request_id="toolreq_browser_002",
            tool_name="browser",
            arguments={"action": 42},
        )
    )

    assert result.outcome == ToolResultOutcome.INVALID_REQUEST


def test_phase4_tool_registry_can_invoke_browser_tool() -> None:
    registry = build_phase4_tool_registry_with_browser(browser_executor=BrowserToolExecutor(_FakeBrowserRunner()))

    result = registry.execute(
        ToolRequest(
            request_id="toolreq_browser_003",
            tool_name="browser",
            arguments={"action": "extract", "target": "testid:nav-link-helpdesk"},
        )
    )

    assert result.outcome == ToolResultOutcome.SUCCESS
    assert result.result is not None
    assert "pageSummary" in result.result
