from __future__ import annotations

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

import pytest

from atlas_env_helpdesk import HelpdeskService
from browser_runner import (
    BrowserAction,
    BrowserCommand,
    BrowserRunnerConfig,
    BrowserRunnerConfigError,
    PlaywrightBrowserRunner,
)


def _playwright_runtime_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        playwright = sync_playwright().start()
        try:
            browser = playwright.chromium.launch(headless=True)
            browser.close()
            return True
        except Exception:
            return False
        finally:
            playwright.stop()
    except Exception:
        return False


def test_browser_runner_rejects_navigation_outside_allowed_paths() -> None:
    runner = PlaywrightBrowserRunner(
        BrowserRunnerConfig(base_url="http://127.0.0.1:3000")
    )

    with pytest.raises(BrowserRunnerConfigError):
        runner.run(BrowserCommand(action=BrowserAction.OPEN, target="/runs"))


@pytest.mark.skipif(not _playwright_runtime_available(), reason="Playwright runtime is not available")
def test_playwright_browser_runner_reads_seeded_helpdesk_surface() -> None:
    helpdesk = HelpdeskService.seeded("seed-phase3-demo")
    ticket = helpdesk.list_ticket_queue().tickets[0]
    html = f"""
    <html>
      <head><title>Helpdesk Queue</title></head>
      <body>
        <main>
          <nav>
            <a data-testid="nav-link-helpdesk" href="/internal/helpdesk">Helpdesk</a>
          </nav>
          <section>
            <p>Internal App</p>
            <h2>Helpdesk Queue</h2>
            <a data-testid="ticket-link-{ticket.ticket_id}" href="/internal/helpdesk/tickets/{ticket.ticket_id}">
              {ticket.title}
            </a>
            <p>{ticket.summary}</p>
          </section>
        </main>
      </body>
    </html>
    """

    with _html_server("/internal/helpdesk", html) as base_url:
        runner = PlaywrightBrowserRunner(
            BrowserRunnerConfig(base_url=base_url, allowed_path_prefixes=("/internal/helpdesk",))
        )
        try:
            observation = runner.run(
                BrowserCommand(action=BrowserAction.OPEN, target="/internal/helpdesk")
            )
        finally:
            runner.close()

    assert observation.title == "Helpdesk Queue"
    assert "Helpdesk Queue" in observation.extracted_text
    assert f"ticket-link-{ticket.ticket_id}" in observation.visible_test_ids


@contextmanager
def _html_server(path: str, html: str):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path != path:
                self.send_response(404)
                self.end_headers()
                return

            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            del format, args

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
