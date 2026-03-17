from __future__ import annotations

from dataclasses import dataclass

from browser_runner import (
    BrowserAction,
    BrowserAutomationRunner,
    BrowserCommand,
    BrowserObservation,
    BrowserRunnerConfigError,
    BrowserScreenshot,
)


@dataclass
class _DemoPageState:
    url: str = "http://127.0.0.1:3000/internal/helpdesk"
    title: str = "Northstar Helpdesk"
    page_summary: str = "Northstar Helpdesk | Helpdesk Queue"
    extracted_text: str = (
        "Northstar Helpdesk Helpdesk Queue Cannot complete MFA after losing phone "
        "Identity proofing has already been completed out of band."
    )
    visible_test_ids: tuple[str, ...] = (
        "nav-link-helpdesk",
        "ticket-queue-table",
        "ticket-row-ticket_mfa_reenrollment_device_loss",
    )


class DeterministicDemoBrowserRunner(BrowserAutomationRunner):
    def __init__(self) -> None:
        self._state = _DemoPageState()

    def run(self, command: BrowserCommand) -> BrowserObservation:
        if command.action == BrowserAction.OPEN:
            target = command.target
            if target != "/internal/helpdesk":
                raise BrowserRunnerConfigError(
                    f"deterministic demo browser only supports /internal/helpdesk, got {target!r}"
                )
            self._state = _DemoPageState()
        elif command.action not in (
            BrowserAction.CLICK,
            BrowserAction.TYPE,
            BrowserAction.EXTRACT,
            BrowserAction.SUBMIT,
        ):
            raise BrowserRunnerConfigError(f"unsupported browser action {command.action.value}")

        return BrowserObservation(
            current_url=self._state.url,
            title=self._state.title,
            page_summary=self._state.page_summary,
            extracted_text=self._state.extracted_text,
            visible_test_ids=self._state.visible_test_ids,
        )

    def capture_screenshot(self, label: str | None = None) -> BrowserScreenshot:
        return BrowserScreenshot(
            current_url=self._state.url,
            title=self._state.title,
            screenshot_bytes=b"\x89PNG\r\nphase4-demo-browser",
            default_filename=f"{label or 'phase4-demo'}-helpdesk.png",
        )

    def close(self) -> None:
        return None
