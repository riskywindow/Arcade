# services/browser-runner

Playwright-based browser runner used by Phase 4 worker tools.

Current Phase 4 scope:

- deterministic local-only browser navigation within the seeded internal app routes
- minimal browser actions: `open`, `click`, `type`, `extract`, `submit`
- screenshot byte capture for later artifact attachment
- structured browser observations with current URL, title, page summary, extracted text, and visible `data-testid` markers

Non-goals:

- generic web browsing outside the configured local console base URL
- screenshot persistence
- stealth/anti-bot behavior
