# apps/console

Next.js operator console shell.

Current scope:

- app boot,
- minimal layout,
- placeholder operator routes for home, runs, scenarios, and system status,
- seeded internal helpdesk routes under `/internal/helpdesk`,
- seeded internal inbox routes under `/internal/inbox`,
- seeded internal wiki routes under `/internal/wiki`,
- typed imports from `@atlas/shared-types`,
- `/runs` operator dashboard with run filtering, demo-run discovery, and a minimal run detail route,
- `/reports/benchmarks/[catalogId]/[benchmarkRunId]` for screenshot-friendly benchmark scorecards and optional baseline comparison,
- approval and kill-switch operator panels backed by the local API,
- no rich replay timeline UI yet.

Local run:

```bash
pnpm --filter @atlas/console dev
```

Future replay UI insertion points:

- `app/runs/` for richer run detail and replay routes
- `app/reports/benchmarks/` for benchmark scorecards and comparison readouts
- `components/` for replay panels and event timeline primitives
- `lib/api/` for typed console-to-API boundaries

Phase 5 local approval smoke path:

- start the API on `http://127.0.0.1:8000`
- start the console
- open `/runs`
- inspect a pending approval card for a paused run
- approve or deny the request locally and refresh the page to confirm the run state changes

Phase 5 local kill-switch smoke path:

- start the API on `http://127.0.0.1:8000`
- start the console
- open `/runs`
- find an active run in the interrupt panel
- submit `Stop run` and refresh to confirm the run moves to `cancelled` once the stop is applied

Phase 3 local helpdesk smoke path:

- start the API on `http://127.0.0.1:8000`
- start the console
- browse `/internal/helpdesk`
- open a seeded ticket, change assignment/status, and add an internal note

Phase 3 local directory smoke path:

- browse `/internal/directory`
- open a seeded employee record
- inspect device, account, ticket, and signal context
- jump from helpdesk ticket detail into related employee records

Phase 3 local wiki smoke path:

- browse `/internal/wiki`
- search for `travel`, `mfa`, or `vpn`
- open a seeded runbook or policy page
- use the wiki as context during helpdesk and directory workflows

Phase 3 local inbox smoke path:

- browse `/internal/inbox`
- open a seeded thread tied to travel, access, contractor, or suspicious-login workflows
- inspect deterministic sender, participant, and message context alongside helpdesk tickets
