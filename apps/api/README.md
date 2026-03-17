# apps/api

FastAPI control-plane API for the live Atlas + Bastion run spine and seeded local environment surfaces.

Current surface:

- `GET /health`
- `POST /runs`
- `GET /runs`
- `GET /runs/{run_id}`
- `GET /runs/{run_id}/events`
- `GET /runs/{run_id}/artifacts`
- `GET /runs/{run_id}/audit`
- `POST /runs/{run_id}/stop`
- `GET /runs/{run_id}/approvals`
- `POST /runs/{run_id}/approvals/{approval_request_id}/approve`
- `POST /runs/{run_id}/approvals/{approval_request_id}/deny`
- seeded environment read surfaces under `/environments/helpdesk`, `/environments/directory`, `/environments/wiki`, and `/environments/inbox`
- seeded helpdesk mutation routes under `/environments/helpdesk/...` for fixture and operator-local use

Ownership:

- HTTP request and response wiring
- dependency assembly for `RunService`
- transport-layer schema mapping for the API surface
- operator approval and run-stop control endpoints backed by the run-event spine

Still deferred:

- task catalog CRUD
- replay aggregation endpoints
- stronger separation between operator-only fixture routes and agent-reachable Bastion paths
- polished approval UI

Boundary note:

- the live agent path does not call the environment mutation routes in this service directly
- agent-requested tool actions must still execute through Bastion from the worker loop
- the seeded helpdesk mutation endpoints remain available only for local fixtures, demos, and operator inspection flows

Local run:

```bash
uv run uvicorn atlas_api.main:app --factory --host 127.0.0.1 --port 8000
```
