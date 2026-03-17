# Atlas + Bastion

Atlas + Bastion is a local-first execution and evaluation lab for autonomous IT/helpdesk agents inside a deterministic synthetic company.

Atlas owns `Environment`, `Scenario`, hidden grading, benchmarking, and `Replay`. Bastion owns tool mediation, `PolicyDecision`, approvals, secrets brokering, and audit.

## Current Status

The repo now has the Phase 5 Bastion path on top of the earlier run spine and seeded environment work: typed `Run` contracts, append-friendly event storage, deterministic synthetic company data, seeded internal surfaces, hidden scenario truth, deterministic graders, a real worker-owned agent loop, and a live Bastion interception layer for tool calls.

What exists now:

- FastAPI API with `/health`, `POST /runs`, `GET /runs`, `GET /runs/{run_id}`, `GET /runs/{run_id}/events`, and `GET /runs/{run_id}/artifacts`
- seeded helpdesk, directory, wiki, and inbox environment APIs
- worker CLI with a deterministic seeded dummy run path and a scripted Phase 3 smoke path
- worker CLI with a deterministic seeded Phase 4 agent demo path for one real scenario
- Bastion-mediated tool interception with allow / deny / require-approval policy outcomes
- approval request records, pause / resume events, local operator approval controls, and kill-switch interruption
- structured Bastion audit records on the run/event spine
- local secrets brokering with non-leakage coverage
- a narrow Docker sandbox wrapper for the allowlisted isolated-command path
- Next.js console with internal helpdesk, directory, wiki, and inbox routes
- deterministic synthetic company builder and reset utilities
- hidden scenario state plus deterministic graders for 5 seeded tasks
- local Postgres, Redis, and MinIO via Docker Compose
- SQL migrations for `runs`, `run_events`, and `run_artifacts`
- smoke checks, linting, typechecking, targeted spine tests, pre-commit hooks, and CI

What does not exist yet:

- a generalized persisted resume path for arbitrary approval-paused runs
- a polished replay UI for Bastion policy, approval, and audit timelines
- production-grade secret management or runtime isolation

## Project Thesis

This repo is not a broad agent platform. It is a narrow lab for answering four concrete questions about autonomous IT/helpdesk agents:

1. Can the agent complete realistic multi-step work?
2. Can it do so under constrained tools and data?
3. Can unsafe actions be denied or routed to approval first?
4. Can failures be replayed, graded, and compared?

## Quickstart

### Prerequisites

- Python 3.12
- Node.js 20
- `uv`
- Docker with Compose support
- `pnpm` via Corepack or local install

### First Run

```bash
make setup
make infra-up
make db-migrate
make smoke
```

If `make smoke` passes, start the app shells in separate terminals:

```bash
make api-dev
make worker-dev
make console-dev
```

Use `make dev` if you want infra started plus a reminder of the app-shell commands.

### What `make smoke` Proves

- the API app can be constructed and `/health` responds
- the worker boot path returns the expected startup state
- the console shell test renders
- Postgres, Redis, and MinIO are running under Docker Compose

### What `make smoke` Does Not Prove

- run creation and retrieval through the Phase 2 API
- event persistence and ordering
- the seeded dummy worker flow
- browser automation
- the full Phase 5 policy-protected demo flow
- replay, grading, or environment logic

### Phase 3 Environment Quick Check

Use the seeded environment surfaces when you want to inspect the current Phase 3 world locally:

```bash
make infra-up
make api-dev
make console-dev
```

Then browse:

- `http://127.0.0.1:3000/internal/helpdesk`
- `http://127.0.0.1:3000/internal/directory`
- `http://127.0.0.1:3000/internal/wiki`
- `http://127.0.0.1:3000/internal/inbox`

### Phase 2 Demo

Use the seeded dummy run flow when you want to verify the implemented run/event spine:

```bash
make infra-up
make api-dev
make phase2-demo-reset
```

Then inspect the canonical run:

```bash
curl http://127.0.0.1:8000/runs/dummy-run-001
curl http://127.0.0.1:8000/runs/dummy-run-001/events
curl http://127.0.0.1:8000/runs/dummy-run-001/artifacts
```

See [docs/demos/README.md](/Users/rishivinodkumar/Arcade/docs/demos/README.md) for the exact expected output.

### Phase 3 Scripted Smoke

Use the temporary scripted actor when you want to prove the seeded environment is actually solvable without a real LLM agent:

```bash
make infra-up
uv run atlas-worker scripted-smoke --run-prefix phase3-smoke
```

This currently exercises:

- `travel-lockout-recovery`
- `shared-drive-access-request`

### Phase 4 Seeded Agent Demo

Use the first real Phase 4 execution path when you want to prove one seeded task can complete end to end:

```bash
make infra-up
make api-dev
make phase4-demo-reset
```

This currently exercises:

- `mfa-reenrollment-device-loss`

The default demo path uses a deterministic stub browser mode for reproducibility. See [docs/demos/README.md](/Users/rishivinodkumar/Arcade/docs/demos/README.md) for the expected output, inspection commands, and the optional live-browser path.

### Phase 5 Policy-Protected Demo

Use the Phase 5 flagship smoke flow when you need the first full Bastion story: denied unsafe shortcut, approval-gated sensitive action, resumed execution, and final success.

```bash
make infra-up
make api-dev
make phase5-demo-reset
```

This currently exercises:

- `travel-lockout-recovery`

See [phase5-policy-protected-demo.md](/Users/rishivinodkumar/Arcade/docs/demos/phase5-policy-protected-demo.md) for the approval step and inspection commands.

Architecture notes for this path:

- [docs/architecture/phase-4-execution-path.md](/Users/rishivinodkumar/Arcade/docs/architecture/phase-4-execution-path.md)
- [docs/architecture/phase-4-execution-contracts.md](/Users/rishivinodkumar/Arcade/docs/architecture/phase-4-execution-contracts.md)
- [docs/architecture/phase-4-model-gateway.md](/Users/rishivinodkumar/Arcade/docs/architecture/phase-4-model-gateway.md)
- [docs/architecture/phase-4-tool-registry.md](/Users/rishivinodkumar/Arcade/docs/architecture/phase-4-tool-registry.md)
- [docs/architecture/phase-4-agent-loop.md](/Users/rishivinodkumar/Arcade/docs/architecture/phase-4-agent-loop.md)

## Troubleshooting

### `make setup` fails

Check that `uv`, Node 20, `pnpm`, and Docker are installed first. If `pnpm` is missing, enable it with Corepack or install it directly.

### `make smoke` says infra is not ready

Run `make infra-up` first, then check container status:

```bash
docker compose -f infra/docker-compose.yml ps
```

### Docker commands fail with permission errors

Your shell likely cannot reach the Docker daemon. Fix Docker Desktop or your local Docker socket permissions before retrying.

### MinIO health check behaves differently on your machine

The container should still appear under `docker compose ps`. Host-side access to `127.0.0.1:9000` can vary by local Docker setup, so treat container status as the primary Phase 1 signal.

### `pre-commit run --all-files` skips everything

This repo currently lives inside a larger git working tree on this machine. `pre-commit --all-files` only evaluates tracked files in the active repository.

## Repo Map

- `apps/api`: control-plane API shell
- `apps/worker`: orchestration worker with deterministic dummy execution, Phase 3 scripted smoke, and the first real Phase 4 agent loop
- `apps/console`: operator console shell
- `services/bastion-gateway`: Bastion service shell
- `services/browser-runner`: Playwright-backed browser automation boundary for seeded internal apps
- `packages/atlas-core`: shared Python domain models, lifecycle rules, serialization, and run persistence contracts
- `packages/atlas-synth`: synthetic company models, canonical fixture, and reset utilities
- `packages/atlas-env-helpdesk`: helpdesk environment contract, scenarios, hidden state, and seeded services
- `packages/atlas-graders`: hidden deterministic grader helpers
- `packages/model-gateway`: provider-agnostic model invocation boundary with a deterministic fake provider for Phase 4
- `packages/shared-types`: shared TypeScript API and event transport contracts
- `infra`: local Docker Compose stack
- `tests`: cross-repo Python smoke and scaffold tests
- `docs`: charter, scope, architecture, security, eval, ADR, and demo notes

Start with:

- [AGENTS.md](/Users/rishivinodkumar/Arcade/AGENTS.md) for repo rules and vocabulary
- [docs/project-charter.md](/Users/rishivinodkumar/Arcade/docs/project-charter.md) for the product thesis
- [docs/architecture/system-overview.md](/Users/rishivinodkumar/Arcade/docs/architecture/system-overview.md) for the control boundary
- [docs/environments/phase-3-environment-overview.md](/Users/rishivinodkumar/Arcade/docs/environments/phase-3-environment-overview.md) for the implemented Phase 3 world
- [docs/architecture/run-lifecycle.md](/Users/rishivinodkumar/Arcade/docs/architecture/run-lifecycle.md) for the intended `Run` flow
- [docs/demos/README.md](/Users/rishivinodkumar/Arcade/docs/demos/README.md) for the current local demo paths

## Common Commands

```bash
make help
make setup
make infra-up
make infra-down
make dev
make smoke
make db-migrate
make db-rollback
make phase2-demo
make phase2-demo-reset
make phase4-demo
make phase4-demo-reset
make phase5-demo
make phase5-demo-reset
make test
make lint
make typecheck
make format
```

## Quality Gates

Python:

- `uv run ruff check .`
- `uv run ruff format .`
- `uv run mypy .`
- `uv run pytest`

TypeScript:

- `pnpm -r lint`
- `pnpm -r typecheck`
- `pnpm -r test`
- `pnpm format`

Top-level shortcuts:

- `make lint`
- `make typecheck`
- `make test`
- `make format`

## Pre-commit Hooks

Install hooks:

```bash
uv run pre-commit install
uv run pre-commit install --hook-type pre-push
```

Run them manually:

```bash
uv run pre-commit run --all-files
uv run pre-commit run --hook-stage pre-push --all-files
```

## Continuous Integration

GitHub Actions runs the same top-level checks on every pull request and every push to `main`:

- `make setup`
- `make lint`
- `make typecheck`
- `make test`

See [`.github/workflows/ci.yml`](/Users/rishivinodkumar/Arcade/.github/workflows/ci.yml).

## Local Infrastructure Defaults

Copy `.env.example` to `.env` if you need overrides. The API and worker now use Postgres for the run spine and Phase 3 environment smoke paths. Redis and MinIO remain provisioned for later phases.

- Postgres: `postgresql://atlas:atlas@127.0.0.1:5432/atlas_bastion`
- Redis: `redis://127.0.0.1:6379/0`
- MinIO API: `http://127.0.0.1:9000`
- MinIO console: `http://127.0.0.1:9001`

## Next Phase Direction

The next phase should build on the Bastion-mediated Phase 5 path rather than redesigning it. Priority follow-ups are replay polish, stronger persisted continuation for approval-paused runs, clearer separation between operator-only fixture routes and agent-reachable paths, and broader eval/demo coverage on the same event-first run spine.
