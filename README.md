# Atlas + Bastion

Atlas + Bastion is a local-first execution and evaluation lab for autonomous IT/helpdesk agents inside a deterministic synthetic company.

Atlas owns `Environment`, `Scenario`, hidden grading, benchmarking, and `Replay`. Bastion owns tool mediation, `PolicyDecision`, approvals, secrets brokering, and audit.

## Current Status

The repo is in Phase 1: the architecture and planning docs are written, the monorepo is scaffolded, local infrastructure is wired, and the API, worker, and console shells all boot.

What exists now:

- FastAPI API shell with `/health`
- worker boot scaffold
- Next.js console shell with placeholder routes
- local Postgres, Redis, and MinIO via Docker Compose
- smoke checks, linting, typechecking, tests, pre-commit hooks, and CI

What does not exist yet:

- real `Run` execution
- seeded `Environment` logic
- Bastion policy behavior
- graders, replay, or scenario persistence
- browser automation

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

- real `Run` execution
- database access beyond container presence
- browser automation
- Bastion policy behavior
- replay, grading, or environment logic

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
- `apps/worker`: orchestration and eval worker shell
- `apps/console`: operator console shell
- `services/bastion-gateway`: Bastion service shell
- `services/browser-runner`: browser service shell
- `packages/atlas-core`: shared Python foundations
- `packages/atlas-synth`: future synthetic company package
- `packages/atlas-env-helpdesk`: future helpdesk environment package
- `packages/atlas-graders`: future hidden grader package
- `packages/model-gateway`: future model/provider boundary
- `packages/shared-types`: shared TypeScript API contracts
- `infra`: local Docker Compose stack
- `tests`: cross-repo Python smoke and scaffold tests
- `docs`: charter, scope, architecture, security, eval, ADR, and demo notes

Start with:

- [AGENTS.md](/Users/rishivinodkumar/Arcade/AGENTS.md) for repo rules and vocabulary
- [docs/project-charter.md](/Users/rishivinodkumar/Arcade/docs/project-charter.md) for the product thesis
- [docs/architecture/system-overview.md](/Users/rishivinodkumar/Arcade/docs/architecture/system-overview.md) for the control boundary
- [docs/architecture/run-lifecycle.md](/Users/rishivinodkumar/Arcade/docs/architecture/run-lifecycle.md) for the intended `Run` flow
- [docs/demos/README.md](/Users/rishivinodkumar/Arcade/docs/demos/README.md) for the current scaffold walkthrough

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

Copy `.env.example` to `.env` if you need overrides. The scaffolds already read these values, even though they do not use persistence or object storage yet.

- Postgres: `postgresql://atlas:atlas@127.0.0.1:5432/atlas_bastion`
- Redis: `redis://127.0.0.1:6379/0`
- MinIO API: `http://127.0.0.1:9000`
- MinIO console: `http://127.0.0.1:9001`

## Next Phase Direction

Phase 2 should start adding real shared schemas, seeded environment state, Bastion-owned tool boundaries, and the first replayable `Run` path. It should not broaden the product scope beyond the narrow IT/helpdesk thesis already set in Phase 0.
