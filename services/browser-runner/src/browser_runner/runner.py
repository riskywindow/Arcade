from __future__ import annotations

from enum import StrEnum
from typing import Protocol, runtime_checkable
from urllib.parse import urljoin, urlparse

from pydantic import BaseModel, ConfigDict, Field


class BrowserRunnerModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class BrowserAction(StrEnum):
    OPEN = "open"
    CLICK = "click"
    TYPE = "type"
    EXTRACT = "extract"
    SUBMIT = "submit"


class BrowserRunnerConfig(BrowserRunnerModel):
    base_url: str = "http://127.0.0.1:3000"
    allowed_path_prefixes: tuple[str, ...] = (
        "/internal/helpdesk",
        "/internal/directory",
        "/internal/wiki",
        "/internal/inbox",
    )
    browser_name: str = "chromium"
    headless: bool = True
    timeout_ms: int = Field(default=15_000, ge=1_000, le=120_000)


class BrowserCommand(BrowserRunnerModel):
    action: BrowserAction
    target: str | None = None
    value: str | None = None


class BrowserObservation(BrowserRunnerModel):
    current_url: str
    title: str
    page_summary: str
    extracted_text: str
    visible_test_ids: tuple[str, ...] = ()


class BrowserScreenshot(BrowserRunnerModel):
    current_url: str
    title: str
    content_type: str = "image/png"
    screenshot_bytes: bytes
    default_filename: str


class BrowserRunnerError(Exception):
    """Base error for browser runner operations."""


class BrowserRunnerConfigError(BrowserRunnerError):
    """Raised when a browser command is structurally invalid."""


class BrowserRunnerExecutionError(BrowserRunnerError):
    """Raised when browser automation fails."""


@runtime_checkable
class BrowserAutomationRunner(Protocol):
    def run(self, command: BrowserCommand) -> BrowserObservation:
        """Execute one browser command and return a structured observation."""

    def capture_screenshot(self, label: str | None = None) -> BrowserScreenshot:
        """Capture a screenshot of the current page."""

    def close(self) -> None:
        """Release browser resources."""


class PlaywrightBrowserRunner:
    def __init__(self, config: BrowserRunnerConfig | None = None) -> None:
        self._config = config or BrowserRunnerConfig()
        self._playwright = None
        self._browser = None
        self._page = None

    def run(self, command: BrowserCommand) -> BrowserObservation:
        try:
            return self._run(command)
        except BrowserRunnerError:
            raise
        except Exception as exc:  # pragma: no cover - defensive wrapper around Playwright
            raise BrowserRunnerExecutionError(str(exc)) from exc

    def close(self) -> None:
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None
        self._page = None

    def capture_screenshot(self, label: str | None = None) -> BrowserScreenshot:
        page = self._page_instance()
        screenshot_bytes = page.screenshot(type="png")
        title = page.title()
        safe_label = _safe_filename_segment(label or "browser")
        path_segment = _safe_filename_segment(urlparse(page.url).path.strip("/") or "root")
        return BrowserScreenshot(
            current_url=page.url,
            title=title,
            screenshot_bytes=screenshot_bytes,
            default_filename=f"{safe_label}-{path_segment}.png",
        )

    def _run(self, command: BrowserCommand) -> BrowserObservation:
        if command.action == BrowserAction.OPEN:
            target = self._require_target(command)
            url = self._resolve_allowed_url(target)
            page = self._page_instance()
            page.goto(url, wait_until="networkidle")
        else:
            page = self._page_instance()

        if command.action == BrowserAction.CLICK:
            page.locator(self._resolve_locator(self._require_target(command))).first.click()
        elif command.action == BrowserAction.TYPE:
            value = command.value
            if value is None:
                raise BrowserRunnerConfigError("type action requires a value")
            page.locator(self._resolve_locator(self._require_target(command))).first.fill(value)
        elif command.action == BrowserAction.SUBMIT:
            page.locator(self._resolve_locator(self._require_target(command))).first.press("Enter")
        elif command.action == BrowserAction.EXTRACT:
            pass
        else:  # pragma: no cover - enum exhaustiveness
            raise BrowserRunnerConfigError(f"unsupported browser action {command.action}")

        return self._observe(page)

    def _page_instance(self):
        if self._page is None:
            sync_playwright = self._load_playwright()
            self._playwright = sync_playwright().start()
            browser_launcher = getattr(self._playwright, self._config.browser_name)
            self._browser = browser_launcher.launch(headless=self._config.headless)
            page = self._browser.new_page(base_url=self._config.base_url)
            page.set_default_timeout(self._config.timeout_ms)
            self._page = page
        return self._page

    def _load_playwright(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover - depends on local install
            raise BrowserRunnerExecutionError(
                "playwright is not installed in the current environment"
            ) from exc
        return sync_playwright

    def _require_target(self, command: BrowserCommand) -> str:
        if not command.target:
            raise BrowserRunnerConfigError(f"{command.action.value} action requires a target")
        return command.target

    def _resolve_allowed_url(self, target: str) -> str:
        url = urljoin(f"{self._config.base_url.rstrip('/')}/", target.lstrip("/"))
        parsed_target = urlparse(url)
        parsed_base = urlparse(self._config.base_url)

        if (
            parsed_target.scheme != parsed_base.scheme
            or parsed_target.netloc != parsed_base.netloc
        ):
            raise BrowserRunnerConfigError("browser navigation must stay on the configured base_url")

        if not any(
            parsed_target.path.startswith(prefix) for prefix in self._config.allowed_path_prefixes
        ):
            raise BrowserRunnerConfigError(
                f"path {parsed_target.path} is outside the allowed internal app surfaces"
            )
        return url

    def _resolve_locator(self, target: str) -> str:
        if target.startswith("testid:"):
            return f'[data-testid="{target.removeprefix("testid:")}"]'
        if target.startswith("css:"):
            return target.removeprefix("css:")
        return target

    def _observe(self, page) -> BrowserObservation:
        title = page.title()
        extracted_text = page.locator("main, body").first.inner_text().strip()
        extracted_text = " ".join(extracted_text.split())
        visible_test_ids = tuple(
            sorted(
                {
                    value
                    for value in page.locator("[data-testid]").evaluate_all(
                        "(elements) => elements.map((element) => element.dataset.testid || '')"
                    )
                    if value
                }
            )
        )
        headings = [
            heading.strip()
            for heading in page.locator("h1, h2").all_inner_texts()
            if heading.strip()
        ]
        summary_parts = [part for part in [title, *headings[:2]] if part]

        return BrowserObservation(
            current_url=page.url,
            title=title,
            page_summary=" | ".join(summary_parts),
            extracted_text=extracted_text[:4000],
            visible_test_ids=visible_test_ids,
        )


def _safe_filename_segment(value: str) -> str:
    cleaned = "".join(char if char.isalnum() else "-" for char in value.lower())
    return cleaned.strip("-") or "artifact"
